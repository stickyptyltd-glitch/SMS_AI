#!/usr/bin/env python3
"""
SynapseFlow AI - Distributor Portal & Commission Management
Multi-tier distributor hierarchy with automated commission tracking

Copyright (c) 2025 Sticky Pty Ltd - ABN: 74689285096
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, render_template_string
from functools import wraps
import jwt
from sales.sales_manager import get_sales_manager, DistributorTier

# Create Blueprint for distributor portal
distributor_bp = Blueprint('distributor', __name__, url_prefix='/distributor')

def require_distributor_auth(f):
    """Decorator to require distributor authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header.split(' ')[1]
        try:
            # Verify JWT token (simplified - use proper JWT library in production)
            payload = jwt.decode(token, os.environ.get('JWT_SECRET', 'dev-secret'), algorithms=['HS256'])
            request.distributor_id = payload['distributor_id']
            return f(*args, **kwargs)
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid authentication token'}), 401
    
    return decorated_function

@distributor_bp.route('/dashboard')
@require_distributor_auth
def dashboard():
    """Distributor dashboard with sales metrics and commissions"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    
    # Get distributor info
    distributor = sales_manager.get_distributor(distributor_id)
    if not distributor:
        return jsonify({'error': 'Distributor not found'}), 404
    
    # Get analytics for different periods
    analytics_30d = sales_manager.get_sales_analytics(distributor_id, 30)
    analytics_90d = sales_manager.get_sales_analytics(distributor_id, 90)
    analytics_ytd = sales_manager.get_sales_analytics(distributor_id, 365)
    
    # Get pending commissions
    pending_commissions = sales_manager.get_pending_commissions(distributor_id)
    
    # Get sub-distributors performance
    sub_distributors = sales_manager.get_sub_distributors(distributor_id)
    
    return jsonify({
        'distributor': {
            'id': distributor.distributor_id,
            'company_name': distributor.company_name,
            'tier': distributor.tier.value,
            'commission_rate': distributor.commission_rate * 100,
            'territory': distributor.territory,
            'ytd_sales': distributor.ytd_sales,
            'sales_target': distributor.sales_target,
            'target_achievement': (distributor.ytd_sales / distributor.sales_target * 100) if distributor.sales_target > 0 else 0
        },
        'analytics': {
            '30_days': analytics_30d,
            '90_days': analytics_90d,
            'year_to_date': analytics_ytd
        },
        'commissions': {
            'pending_amount': sum(c['amount'] for c in pending_commissions),
            'pending_count': len(pending_commissions),
            'details': pending_commissions
        },
        'sub_distributors': sub_distributors
    })

@distributor_bp.route('/hierarchy')
@require_distributor_auth
def get_hierarchy():
    """Get complete distributor hierarchy tree"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    
    def build_hierarchy_tree(parent_id: str, level: int = 0) -> Dict[str, Any]:
        """Recursively build hierarchy tree"""
        distributor = sales_manager.get_distributor(parent_id)
        if not distributor:
            return None
        
        # Get direct sub-distributors
        sub_distributors = []
        with sales_manager._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT distributor_id FROM distributors 
                WHERE parent_distributor_id = ? AND status = 'active'
            ''', (parent_id,))
            
            for (sub_id,) in cursor.fetchall():
                sub_tree = build_hierarchy_tree(sub_id, level + 1)
                if sub_tree:
                    sub_distributors.append(sub_tree)
        
        # Get performance metrics
        analytics = sales_manager.get_sales_analytics(parent_id, 90)
        
        return {
            'distributor_id': distributor.distributor_id,
            'company_name': distributor.company_name,
            'tier': distributor.tier.value,
            'level': level,
            'commission_rate': distributor.commission_rate * 100,
            'territory': distributor.territory,
            'ytd_sales': distributor.ytd_sales,
            'recent_performance': {
                'total_sales': analytics['total_sales'],
                'total_revenue': analytics['total_revenue'],
                'win_rate': analytics['win_rate']
            },
            'sub_distributors': sub_distributors,
            'sub_distributor_count': len(sub_distributors)
        }
    
    hierarchy = build_hierarchy_tree(distributor_id)
    return jsonify(hierarchy)

@distributor_bp.route('/commission-calculator')
@require_distributor_auth
def commission_calculator():
    """Calculate potential commissions for different sale amounts"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    sale_amount = float(request.args.get('amount', 1000))
    
    distributor = sales_manager.get_distributor(distributor_id)
    if not distributor:
        return jsonify({'error': 'Distributor not found'}), 404
    
    # Calculate multi-tier commissions
    tiers = []
    current_distributor_id = distributor_id
    tier_level = 1
    
    while current_distributor_id and tier_level <= 3:
        current_distributor = sales_manager.get_distributor(current_distributor_id)
        if not current_distributor:
            break
        
        # Commission rates decrease by tier level
        commission_rate = current_distributor.commission_rate * (0.6 ** (tier_level - 1))
        commission_amount = sale_amount * commission_rate
        
        tiers.append({
            'level': tier_level,
            'distributor_id': current_distributor.distributor_id,
            'company_name': current_distributor.company_name,
            'tier': current_distributor.tier.value,
            'base_rate': current_distributor.commission_rate * 100,
            'effective_rate': commission_rate * 100,
            'commission_amount': commission_amount
        })
        
        current_distributor_id = current_distributor.parent_distributor_id
        tier_level += 1
    
    total_commissions = sum(t['commission_amount'] for t in tiers)
    
    return jsonify({
        'sale_amount': sale_amount,
        'total_commissions': total_commissions,
        'commission_percentage': (total_commissions / sale_amount * 100) if sale_amount > 0 else 0,
        'tier_breakdown': tiers
    })

@distributor_bp.route('/upgrade-tier', methods=['POST'])
@require_distributor_auth
def upgrade_tier():
    """Request tier upgrade based on performance"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    
    distributor = sales_manager.get_distributor(distributor_id)
    if not distributor:
        return jsonify({'error': 'Distributor not found'}), 404
    
    # Get YTD performance
    analytics = sales_manager.get_sales_analytics(distributor_id, 365)
    
    # Define tier upgrade requirements
    tier_requirements = {
        DistributorTier.AUTHORIZED: {'min_revenue': 0, 'min_sales': 0},
        DistributorTier.PREFERRED: {'min_revenue': 50000, 'min_sales': 10},
        DistributorTier.PREMIUM: {'min_revenue': 150000, 'min_sales': 25},
        DistributorTier.MASTER: {'min_revenue': 500000, 'min_sales': 75},
        DistributorTier.EXCLUSIVE: {'min_revenue': 1500000, 'min_sales': 200}
    }
    
    current_tier = distributor.tier
    next_tier = None
    
    # Determine next available tier
    tier_order = [DistributorTier.AUTHORIZED, DistributorTier.PREFERRED, 
                  DistributorTier.PREMIUM, DistributorTier.MASTER, DistributorTier.EXCLUSIVE]
    
    current_index = tier_order.index(current_tier)
    if current_index < len(tier_order) - 1:
        next_tier = tier_order[current_index + 1]
    
    if not next_tier:
        return jsonify({
            'eligible': False,
            'message': 'Already at highest tier',
            'current_tier': current_tier.value
        })
    
    requirements = tier_requirements[next_tier]
    eligible = (analytics['total_revenue'] >= requirements['min_revenue'] and 
                analytics['won_deals'] >= requirements['min_sales'])
    
    return jsonify({
        'eligible': eligible,
        'current_tier': current_tier.value,
        'next_tier': next_tier.value,
        'requirements': requirements,
        'current_performance': {
            'revenue': analytics['total_revenue'],
            'sales': analytics['won_deals']
        },
        'gap_analysis': {
            'revenue_gap': max(0, requirements['min_revenue'] - analytics['total_revenue']),
            'sales_gap': max(0, requirements['min_sales'] - analytics['won_deals'])
        }
    })

@distributor_bp.route('/white-label-config')
@require_distributor_auth
def get_white_label_config():
    """Get white-label customization settings"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    
    distributor = sales_manager.get_distributor(distributor_id)
    if not distributor:
        return jsonify({'error': 'Distributor not found'}), 404
    
    # Check if white-label is available for this tier
    white_label_tiers = [DistributorTier.PREMIUM, DistributorTier.MASTER, DistributorTier.EXCLUSIVE]
    if distributor.tier not in white_label_tiers:
        return jsonify({
            'available': False,
            'message': f'White-label customization requires {", ".join([t.value for t in white_label_tiers])} tier',
            'current_tier': distributor.tier.value
        })
    
    return jsonify({
        'available': True,
        'current_config': distributor.custom_branding,
        'customizable_elements': [
            'logo_url',
            'company_name',
            'primary_color',
            'secondary_color',
            'custom_domain',
            'support_email',
            'support_phone',
            'terms_url',
            'privacy_url'
        ]
    })

@distributor_bp.route('/white-label-config', methods=['POST'])
@require_distributor_auth
def update_white_label_config():
    """Update white-label customization settings"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    
    distributor = sales_manager.get_distributor(distributor_id)
    if not distributor:
        return jsonify({'error': 'Distributor not found'}), 404
    
    # Check white-label availability
    white_label_tiers = [DistributorTier.PREMIUM, DistributorTier.MASTER, DistributorTier.EXCLUSIVE]
    if distributor.tier not in white_label_tiers:
        return jsonify({'error': 'White-label not available for your tier'}), 403
    
    branding_data = request.json
    
    # Validate and sanitize branding data
    allowed_fields = ['logo_url', 'company_name', 'primary_color', 'secondary_color',
                      'custom_domain', 'support_email', 'support_phone', 'terms_url', 'privacy_url']
    
    filtered_branding = {k: v for k, v in branding_data.items() if k in allowed_fields}
    
    # Update in database
    with sales_manager._get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE distributors 
            SET custom_branding = ? 
            WHERE distributor_id = ?
        ''', (json.dumps(filtered_branding), distributor_id))
        conn.commit()
    
    return jsonify({
        'success': True,
        'message': 'White-label configuration updated',
        'config': filtered_branding
    })

@distributor_bp.route('/sales-pipeline')
@require_distributor_auth
def get_sales_pipeline():
    """Get sales pipeline for distributor"""
    sales_manager = get_sales_manager()
    distributor_id = request.distributor_id
    
    with sales_manager._get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, c.company_name, c.contact_name, c.email
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.distributor_id = ?
            ORDER BY s.created_date DESC
        ''', (distributor_id,))
        
        pipeline = []
        for row in cursor.fetchall():
            pipeline.append({
                'sale_id': row[0],
                'customer': {
                    'company_name': row[9],
                    'contact_name': row[10],
                    'email': row[11]
                },
                'product_tier': row[3],
                'amount': row[4],
                'commission_amount': row[5],
                'stage': row[6],
                'created_date': row[7],
                'closed_date': row[8],
                'notes': row[12] if len(row) > 12 else ''
            })
    
    # Group by stage
    by_stage = {}
    for sale in pipeline:
        stage = sale['stage']
        if stage not in by_stage:
            by_stage[stage] = []
        by_stage[stage].append(sale)
    
    return jsonify({
        'total_opportunities': len(pipeline),
        'by_stage': by_stage,
        'pipeline_value': sum(s['amount'] for s in pipeline if s['stage'] not in ['closed_won', 'closed_lost']),
        'won_value': sum(s['amount'] for s in pipeline if s['stage'] == 'closed_won'),
        'potential_commissions': sum(s['commission_amount'] for s in pipeline if s['stage'] not in ['closed_won', 'closed_lost'])
    })

# Add to sales manager for database connection helper
def _get_db_connection(self):
    """Get database connection"""
    import sqlite3
    return sqlite3.connect(self.db_path)

# Monkey patch the method
get_sales_manager()._get_db_connection = _get_db_connection.__get__(get_sales_manager(), type(get_sales_manager()))

def init_distributor_portal(app):
    """Initialize distributor portal with Flask app"""
    app.register_blueprint(distributor_bp)
    return distributor_bp