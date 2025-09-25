#!/usr/bin/env python3
"""
SynapseFlow AI - Sales & Distributor Management System
Enterprise-grade sales pipeline, distributor hierarchy, and commission tracking

Copyright (c) 2025 Sticky Pty Ltd - ABN: 74689285096
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import sqlite3
from cryptography.fernet import Fernet
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class DistributorTier(Enum):
    """Distributor tier levels with different commission rates"""
    AUTHORIZED = "authorized"           # 15% commission
    PREFERRED = "preferred"             # 20% commission  
    PREMIUM = "premium"                 # 25% commission
    MASTER = "master"                   # 30% commission
    EXCLUSIVE = "exclusive"             # 35% commission

class SaleStage(Enum):
    """Sales pipeline stages"""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

@dataclass
class Distributor:
    """Distributor/Partner information"""
    distributor_id: str
    company_name: str
    contact_name: str
    email: str
    phone: str
    tier: DistributorTier
    territory: str
    commission_rate: float
    parent_distributor_id: Optional[str] = None
    registration_date: str = None
    status: str = "active"
    custom_branding: Dict[str, Any] = None
    sales_target: float = 0.0
    ytd_sales: float = 0.0

@dataclass
class Customer:
    """Customer information"""
    customer_id: str
    company_name: str
    contact_name: str
    email: str
    phone: str
    country: str
    industry: str
    registration_date: str
    distributor_id: Optional[str] = None
    total_spent: float = 0.0
    licenses_owned: List[str] = None

@dataclass
class Sale:
    """Sales transaction"""
    sale_id: str
    customer_id: str
    distributor_id: Optional[str]
    product_tier: str
    amount: float
    commission_amount: float
    stage: SaleStage
    created_date: str
    closed_date: Optional[str] = None
    license_keys: List[str] = None
    notes: str = ""

@dataclass
class License:
    """Software license record"""
    license_id: str
    customer_id: str
    distributor_id: Optional[str]
    product_tier: str
    activation_key: str
    issue_date: str
    expiry_date: str
    hardware_id: Optional[str] = None
    status: str = "active"
    customizations: Dict[str, Any] = None

class SalesManager:
    """Comprehensive sales and distributor management system"""
    
    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.sales_dir = os.path.join(data_dir, "sales")
        self.db_path = os.path.join(self.sales_dir, "sales.db")
        
        os.makedirs(self.sales_dir, exist_ok=True)
        self._init_database()
        
        # Load encryption key for sensitive data
        self.encryption_key = self._get_encryption_key()
        
    def _init_database(self):
        """Initialize sales database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Distributors table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS distributors (
                    distributor_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    tier TEXT NOT NULL,
                    territory TEXT,
                    commission_rate REAL NOT NULL,
                    parent_distributor_id TEXT,
                    registration_date TEXT,
                    status TEXT DEFAULT 'active',
                    custom_branding TEXT,
                    sales_target REAL DEFAULT 0,
                    ytd_sales REAL DEFAULT 0,
                    FOREIGN KEY (parent_distributor_id) REFERENCES distributors (distributor_id)
                )
            ''')
            
            # Customers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    country TEXT,
                    industry TEXT,
                    registration_date TEXT,
                    distributor_id TEXT,
                    total_spent REAL DEFAULT 0,
                    FOREIGN KEY (distributor_id) REFERENCES distributors (distributor_id)
                )
            ''')
            
            # Sales table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    distributor_id TEXT,
                    product_tier TEXT NOT NULL,
                    amount REAL NOT NULL,
                    commission_amount REAL NOT NULL,
                    stage TEXT NOT NULL,
                    created_date TEXT,
                    closed_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                    FOREIGN KEY (distributor_id) REFERENCES distributors (distributor_id)
                )
            ''')
            
            # Licenses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS licenses (
                    license_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    distributor_id TEXT,
                    product_tier TEXT NOT NULL,
                    activation_key TEXT NOT NULL,
                    issue_date TEXT,
                    expiry_date TEXT,
                    hardware_id TEXT,
                    status TEXT DEFAULT 'active',
                    customizations TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                    FOREIGN KEY (distributor_id) REFERENCES distributors (distributor_id)
                )
            ''')
            
            # Commission tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS commissions (
                    commission_id TEXT PRIMARY KEY,
                    sale_id TEXT NOT NULL,
                    distributor_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    tier_level INTEGER NOT NULL,
                    payment_date TEXT,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (sale_id) REFERENCES sales (sale_id),
                    FOREIGN KEY (distributor_id) REFERENCES distributors (distributor_id)
                )
            ''')
            
            conn.commit()
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = os.path.join(self.sales_dir, ".sales_key")
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            return key
    
    # Distributor Management
    def register_distributor(self, distributor_data: Dict[str, Any]) -> str:
        """Register new distributor"""
        distributor_id = f"DIST-{uuid.uuid4().hex[:8].upper()}"
        
        # Set commission rate based on tier
        tier = DistributorTier(distributor_data["tier"])
        commission_rates = {
            DistributorTier.AUTHORIZED: 0.15,
            DistributorTier.PREFERRED: 0.20,
            DistributorTier.PREMIUM: 0.25,
            DistributorTier.MASTER: 0.30,
            DistributorTier.EXCLUSIVE: 0.35
        }
        
        distributor = Distributor(
            distributor_id=distributor_id,
            company_name=distributor_data["company_name"],
            contact_name=distributor_data["contact_name"],
            email=distributor_data["email"],
            phone=distributor_data.get("phone", ""),
            tier=tier,
            territory=distributor_data.get("territory", ""),
            commission_rate=commission_rates[tier],
            parent_distributor_id=distributor_data.get("parent_distributor_id"),
            registration_date=datetime.now(timezone.utc).isoformat(),
            custom_branding=distributor_data.get("custom_branding", {}),
            sales_target=distributor_data.get("sales_target", 0.0)
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO distributors (
                    distributor_id, company_name, contact_name, email, phone,
                    tier, territory, commission_rate, parent_distributor_id,
                    registration_date, custom_branding, sales_target
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                distributor.distributor_id,
                distributor.company_name,
                distributor.contact_name,
                distributor.email,
                distributor.phone,
                distributor.tier.value,
                distributor.territory,
                distributor.commission_rate,
                distributor.parent_distributor_id,
                distributor.registration_date,
                json.dumps(distributor.custom_branding),
                distributor.sales_target
            ))
            conn.commit()
        
        return distributor_id
    
    def get_distributor(self, distributor_id: str) -> Optional[Distributor]:
        """Get distributor information"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM distributors WHERE distributor_id = ?', (distributor_id,))
            row = cursor.fetchone()
            
            if row:
                return Distributor(
                    distributor_id=row[0],
                    company_name=row[1],
                    contact_name=row[2],
                    email=row[3],
                    phone=row[4],
                    tier=DistributorTier(row[5]),
                    territory=row[6],
                    commission_rate=row[7],
                    parent_distributor_id=row[8],
                    registration_date=row[9],
                    status=row[10],
                    custom_branding=json.loads(row[11]) if row[11] else {},
                    sales_target=row[12],
                    ytd_sales=row[13]
                )
        return None
    
    # Customer Management
    def register_customer(self, customer_data: Dict[str, Any]) -> str:
        """Register new customer"""
        customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"
        
        customer = Customer(
            customer_id=customer_id,
            company_name=customer_data["company_name"],
            contact_name=customer_data["contact_name"],
            email=customer_data["email"],
            phone=customer_data.get("phone", ""),
            country=customer_data.get("country", ""),
            industry=customer_data.get("industry", ""),
            registration_date=datetime.now(timezone.utc).isoformat(),
            distributor_id=customer_data.get("distributor_id"),
            licenses_owned=[]
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO customers (
                    customer_id, company_name, contact_name, email, phone,
                    country, industry, registration_date, distributor_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer.customer_id,
                customer.company_name,
                customer.contact_name,
                customer.email,
                customer.phone,
                customer.country,
                customer.industry,
                customer.registration_date,
                customer.distributor_id
            ))
            conn.commit()
        
        return customer_id
    
    # Sales Pipeline Management
    def create_sale(self, sale_data: Dict[str, Any]) -> str:
        """Create new sales opportunity"""
        sale_id = f"SALE-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate commission
        commission_amount = 0.0
        if sale_data.get("distributor_id"):
            distributor = self.get_distributor(sale_data["distributor_id"])
            if distributor:
                commission_amount = sale_data["amount"] * distributor.commission_rate
        
        sale = Sale(
            sale_id=sale_id,
            customer_id=sale_data["customer_id"],
            distributor_id=sale_data.get("distributor_id"),
            product_tier=sale_data["product_tier"],
            amount=sale_data["amount"],
            commission_amount=commission_amount,
            stage=SaleStage(sale_data.get("stage", "lead")),
            created_date=datetime.now(timezone.utc).isoformat(),
            notes=sale_data.get("notes", "")
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sales (
                    sale_id, customer_id, distributor_id, product_tier,
                    amount, commission_amount, stage, created_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sale.sale_id,
                sale.customer_id,
                sale.distributor_id,
                sale.product_tier,
                sale.amount,
                sale.commission_amount,
                sale.stage.value,
                sale.created_date,
                sale.notes
            ))
            conn.commit()
        
        return sale_id
    
    def update_sale_stage(self, sale_id: str, new_stage: SaleStage, notes: str = "") -> bool:
        """Update sales opportunity stage"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            update_data = [new_stage.value, notes, sale_id]
            query = 'UPDATE sales SET stage = ?, notes = ?'
            
            # If closing the sale, set closed date and generate license
            if new_stage in [SaleStage.CLOSED_WON, SaleStage.CLOSED_LOST]:
                query += ', closed_date = ?'
                update_data.insert(-1, datetime.now(timezone.utc).isoformat())
                
                if new_stage == SaleStage.CLOSED_WON:
                    # Generate license automatically
                    self._generate_license_for_sale(sale_id)
            
            query += ' WHERE sale_id = ?'
            cursor.execute(query, update_data)
            conn.commit()
            
            return cursor.rowcount > 0
    
    def _generate_license_for_sale(self, sale_id: str):
        """Generate software license for completed sale"""
        from tools.license_issuer import main as generate_license_key
        import subprocess
        import tempfile
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sales WHERE sale_id = ?', (sale_id,))
            sale_row = cursor.fetchone()
            
            if not sale_row:
                return None
            
            # Get customer info
            cursor.execute('SELECT * FROM customers WHERE customer_id = ?', (sale_row[1],))
            customer_row = cursor.fetchone()
            
            if not customer_row:
                return None
            
            license_id = f"LIC-{uuid.uuid4().hex[:8].upper()}"
            
            # Generate activation key using license issuer
            expiry_date = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d")
            
            try:
                result = subprocess.run([
                    'python', 'tools/license_issuer.py',
                    '--license-id', license_id,
                    '--tier', sale_row[3],  # product_tier
                    '--expires', expiry_date,
                    '--hardware-id', 'ANY',
                    '--features', self._get_features_for_tier(sale_row[3])
                ], capture_output=True, text=True, cwd='/home/sticky/Desktop/SMS_AI')
                
                if result.returncode == 0:
                    activation_key = result.stdout.strip()
                    
                    # Store license in database
                    cursor.execute('''
                        INSERT INTO licenses (
                            license_id, customer_id, distributor_id, product_tier,
                            activation_key, issue_date, expiry_date, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        license_id,
                        sale_row[1],  # customer_id
                        sale_row[2],  # distributor_id
                        sale_row[3],  # product_tier
                        activation_key,
                        datetime.now(timezone.utc).isoformat(),
                        expiry_date,
                        'active'
                    ))
                    
                    conn.commit()
                    
                    # Send license via email
                    self._send_license_email(customer_row[3], license_id, activation_key, sale_row[3])
                    
                    return license_id
                    
            except Exception as e:
                print(f"License generation failed: {e}")
                return None
    
    def _get_features_for_tier(self, tier: str) -> str:
        """Get feature set for product tier"""
        features_map = {
            "starter": "core,basic_ai",
            "professional": "core,advanced_ai,integrations,analytics",
            "enterprise": "core,advanced_ai,integrations,analytics,white_label,sso",
            "enterprise_plus": "core,advanced_ai,integrations,analytics,white_label,sso,custom_development"
        }
        return features_map.get(tier, "core")
    
    def _send_license_email(self, customer_email: str, license_id: str, activation_key: str, tier: str):
        """Send license activation email to customer"""
        try:
            smtp_host = os.environ.get('SMTP_HOST', 'localhost')
            smtp_port = int(os.environ.get('SMTP_PORT', '587'))
            smtp_user = os.environ.get('SMTP_USER', '')
            smtp_password = os.environ.get('SMTP_PASSWORD', '')
            from_email = os.environ.get('FROM_EMAIL', 'noreply@synapseflow.ai')
            
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = customer_email
            msg['Subject'] = f"SynapseFlow AI License - {license_id}"
            
            body = f"""
Thank you for purchasing SynapseFlow AI {tier.title()}!

Your License Details:
- License ID: {license_id}
- Product Tier: {tier.title()}
- Activation Key: {activation_key}

To activate your license:
1. Install SynapseFlow AI
2. Use the activation key above
3. Your license is valid for 1 year from today

Need help? Contact support@synapseflow.ai

Best regards,
SynapseFlow AI Team
Sticky Pty Ltd - ABN: 74689285096
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
                
        except Exception as e:
            print(f"Failed to send license email: {e}")
    
    # Commission Management
    def calculate_multi_tier_commissions(self, sale_id: str) -> List[Dict[str, Any]]:
        """Calculate commissions for multi-tier distributor hierarchy"""
        commissions = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sales WHERE sale_id = ?', (sale_id,))
            sale_row = cursor.fetchone()
            
            if not sale_row or not sale_row[2]:  # No distributor
                return commissions
            
            current_distributor_id = sale_row[2]
            tier_level = 1
            remaining_amount = sale_row[4]  # Sale amount
            
            while current_distributor_id and tier_level <= 3:  # Max 3 levels
                distributor = self.get_distributor(current_distributor_id)
                if not distributor:
                    break
                
                # Commission rates decrease by tier level
                commission_rate = distributor.commission_rate * (0.6 ** (tier_level - 1))
                commission_amount = remaining_amount * commission_rate
                
                commission_id = f"COMM-{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute('''
                    INSERT INTO commissions (
                        commission_id, sale_id, distributor_id, amount, tier_level
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (commission_id, sale_id, current_distributor_id, commission_amount, tier_level))
                
                commissions.append({
                    "commission_id": commission_id,
                    "distributor_id": current_distributor_id,
                    "distributor_name": distributor.company_name,
                    "tier_level": tier_level,
                    "amount": commission_amount,
                    "rate": commission_rate
                })
                
                current_distributor_id = distributor.parent_distributor_id
                tier_level += 1
            
            conn.commit()
        
        return commissions
    
    # Analytics and Reporting
    def get_sales_analytics(self, distributor_id: str = None, period_days: int = 30) -> Dict[str, Any]:
        """Get sales analytics and performance metrics"""
        start_date = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            base_query = '''
                SELECT 
                    COUNT(*) as total_sales,
                    SUM(amount) as total_revenue,
                    AVG(amount) as average_deal_size,
                    SUM(commission_amount) as total_commissions,
                    COUNT(CASE WHEN stage = 'closed_won' THEN 1 END) as won_deals,
                    COUNT(CASE WHEN stage = 'closed_lost' THEN 1 END) as lost_deals
                FROM sales 
                WHERE created_date >= ?
            '''
            
            if distributor_id:
                base_query += ' AND distributor_id = ?'
                cursor.execute(base_query, (start_date, distributor_id))
            else:
                cursor.execute(base_query, (start_date,))
            
            analytics = cursor.fetchone()
            
            return {
                "period_days": period_days,
                "total_sales": analytics[0] or 0,
                "total_revenue": analytics[1] or 0.0,
                "average_deal_size": analytics[2] or 0.0,
                "total_commissions": analytics[3] or 0.0,
                "won_deals": analytics[4] or 0,
                "lost_deals": analytics[5] or 0,
                "win_rate": (analytics[4] / (analytics[4] + analytics[5]) * 100) if (analytics[4] + analytics[5]) > 0 else 0
            }
    
    def get_distributor_leaderboard(self, period_days: int = 30) -> List[Dict[str, Any]]:
        """Get top performing distributors"""
        start_date = (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    d.distributor_id,
                    d.company_name,
                    d.tier,
                    COUNT(s.sale_id) as total_sales,
                    SUM(s.amount) as total_revenue,
                    SUM(s.commission_amount) as total_commissions
                FROM distributors d
                LEFT JOIN sales s ON d.distributor_id = s.distributor_id 
                    AND s.created_date >= ? 
                    AND s.stage = 'closed_won'
                WHERE d.status = 'active'
                GROUP BY d.distributor_id
                ORDER BY total_revenue DESC
                LIMIT 10
            ''', (start_date,))
            
            return [
                {
                    "distributor_id": row[0],
                    "company_name": row[1],
                    "tier": row[2],
                    "total_sales": row[3] or 0,
                    "total_revenue": row[4] or 0.0,
                    "total_commissions": row[5] or 0.0
                }
                for row in cursor.fetchall()
            ]

# Global sales manager instance
_sales_manager = None

def get_sales_manager() -> SalesManager:
    """Get global sales manager instance"""
    global _sales_manager
    if _sales_manager is None:
        _sales_manager = SalesManager()
    return _sales_manager