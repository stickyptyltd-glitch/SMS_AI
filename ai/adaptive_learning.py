#!/usr/bin/env python3
"""
Adaptive Learning System
Advanced machine learning for continuous improvement of SMS responses
based on user feedback, conversation patterns, and success metrics.
"""

import os
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import sqlite3
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import pickle

@dataclass
class LearningExample:
    """A learning example from user interactions"""
    input_text: str
    response_text: str
    user_feedback: float  # -1 to 1 scale
    context: Dict[str, Any]
    timestamp: str
    contact: str
    success_metrics: Dict[str, float]

@dataclass
class ResponsePattern:
    """Learned response pattern"""
    pattern_id: str
    input_features: List[str]
    response_template: str
    success_rate: float
    usage_count: int
    last_updated: str
    confidence_score: float

class FeatureExtractor:
    """Extracts features from messages for learning"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.is_fitted = False
    
    def extract_features(self, text: str, context: Dict = None) -> Dict[str, Any]:
        """Extract comprehensive features from text"""
        features = {}

        # Basic text features
        features['length'] = len(text)
        features['word_count'] = len(text.split())
        features['sentence_count'] = len([s for s in text.split('.') if s.strip()])
        features['avg_word_length'] = np.mean([len(word) for word in text.split()]) if text.split() else 0

        # Enhanced sentiment indicators
        positive_words = ['good', 'great', 'awesome', 'happy', 'love', 'excellent', 'amazing',
                         'wonderful', 'fantastic', 'brilliant', 'perfect', 'outstanding', 'superb']
        negative_words = ['bad', 'terrible', 'hate', 'awful', 'horrible', 'sad', 'angry',
                         'disappointed', 'frustrated', 'annoyed', 'upset', 'worried', 'stressed']
        question_words = ['what', 'when', 'where', 'why', 'how', 'who', 'which', 'can', 'could', 'would']
        urgency_words = ['urgent', 'asap', 'immediately', 'emergency', 'help', 'quick', 'fast', 'now']

        text_lower = text.lower()
        words = text_lower.split()

        features['positive_word_count'] = sum(1 for word in words if word in positive_words)
        features['negative_word_count'] = sum(1 for word in words if word in negative_words)
        features['question_word_count'] = sum(1 for word in words if word in question_words)
        features['urgency_word_count'] = sum(1 for word in words if word in urgency_words)

        # Advanced linguistic features
        features['exclamation_count'] = text.count('!')
        features['question_count'] = text.count('?')
        features['emoji_count'] = sum(1 for char in text if ord(char) > 127)
        features['caps_ratio'] = sum(1 for char in text if char.isupper()) / len(text) if text else 0
        features['punctuation_density'] = sum(1 for char in text if not char.isalnum() and not char.isspace()) / len(text) if text else 0

        # Sentiment analysis
        positive_words = ['good', 'great', 'awesome', 'happy', 'love', 'excellent', 'amazing',
                         'wonderful', 'fantastic', 'brilliant', 'perfect', 'outstanding', 'superb']
        negative_words = ['bad', 'terrible', 'hate', 'awful', 'horrible', 'sad', 'angry',
                         'disappointed', 'frustrated', 'annoyed', 'upset', 'worried', 'stressed']

        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)

        total_words = len(words)
        if total_words > 0:
            sentiment_score = (positive_count - negative_count) / total_words
        else:
            sentiment_score = 0

        features['sentiment_score'] = sentiment_score

        # Semantic features
        features['contains_greeting'] = any(word in text_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good evening'])
        features['contains_goodbye'] = any(word in text_lower for word in ['bye', 'goodbye', 'see you', 'talk later'])
        features['contains_thanks'] = any(word in text_lower for word in ['thank', 'thanks', 'appreciate'])
        features['contains_apology'] = any(word in text_lower for word in ['sorry', 'apologize', 'my bad'])

        # Context features
        if context:
            features['time_of_day'] = context.get('time_of_day', 12)
            features['day_of_week'] = context.get('day_of_week', 1)
            features['conversation_length'] = context.get('conversation_length', 1)
            features['last_response_time'] = context.get('last_response_time', 0)
            features['user_mood'] = context.get('user_mood', 'neutral')
            features['conversation_topic'] = context.get('conversation_topic', 'general')

        feature_vector = list(features.values())
        return feature_vector
    
    def fit_tfidf(self, texts: List[str]):
        """Fit TF-IDF vectorizer on text corpus"""
        self.tfidf_vectorizer.fit(texts)
        self.is_fitted = True
    
    def get_tfidf_features(self, text: str) -> np.ndarray:
        """Get TF-IDF features for text"""
        if not self.is_fitted:
            return np.array([])
        return self.tfidf_vectorizer.transform([text]).toarray()[0]

class AdaptiveLearningSystem:
    """Advanced learning system for SMS AI improvement"""
    
    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.learning_dir = os.path.join(data_dir, "learning")
        os.makedirs(self.learning_dir, exist_ok=True)
        
        # Initialize components
        self.feature_extractor = FeatureExtractor()
        self.learning_examples = []
        self.response_patterns = {}
        self.user_preferences = defaultdict(dict)
        
        # Database for learning data
        self.db_path = os.path.join(self.learning_dir, "learning.db")
        self._init_database()
        
        # Load existing data
        self._load_learning_data()
        
        # Learning parameters
        self.min_examples_for_pattern = 5
        self.pattern_confidence_threshold = 0.7
        self.feedback_weight_decay = 0.95  # Older feedback has less weight
        
    def _init_database(self):
        """Initialize learning database, recovering from corruption if needed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_examples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    user_feedback REAL,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    contact TEXT,
                    success_metrics TEXT
                )
            """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS response_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    input_features TEXT,
                    response_template TEXT,
                    success_rate REAL,
                    usage_count INTEGER,
                    last_updated TEXT,
                    confidence_score REAL
                )
            """)
                
                conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    contact TEXT,
                    preference_key TEXT,
                    preference_value TEXT,
                    confidence REAL,
                    last_updated TEXT,
                    PRIMARY KEY (contact, preference_key)
                )
            """)
        except sqlite3.DatabaseError as e:
            # Handle corrupted database files gracefully
            if "file is not a database" in str(e).lower():
                try:
                    if os.path.exists(self.db_path):
                        os.remove(self.db_path)
                except Exception:
                    pass
                # Recreate a fresh database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS learning_examples (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            input_text TEXT NOT NULL,
                            response_text TEXT NOT NULL,
                            user_feedback REAL,
                            context TEXT,
                            timestamp TEXT NOT NULL,
                            contact TEXT,
                            success_metrics TEXT
                        )
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS response_patterns (
                            pattern_id TEXT PRIMARY KEY,
                            input_features TEXT,
                            response_template TEXT,
                            success_rate REAL,
                            usage_count INTEGER,
                            last_updated TEXT,
                            confidence_score REAL
                        )
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS user_preferences (
                            contact TEXT,
                            preference_key TEXT,
                            preference_value TEXT,
                            confidence REAL,
                            last_updated TEXT,
                            PRIMARY KEY (contact, preference_key)
                        )
                    """)
            else:
                raise
    
    def _load_learning_data(self):
        """Load existing learning data from database"""
        with sqlite3.connect(self.db_path) as conn:
            # Load learning examples
            cursor = conn.execute("""
                SELECT input_text, response_text, user_feedback, context, 
                       timestamp, contact, success_metrics
                FROM learning_examples
                ORDER BY timestamp DESC
                LIMIT 10000
            """)
            
            for row in cursor.fetchall():
                example = LearningExample(
                    input_text=row[0],
                    response_text=row[1],
                    user_feedback=row[2] or 0.0,
                    context=json.loads(row[3]) if row[3] else {},
                    timestamp=row[4],
                    contact=row[5] or "Unknown",
                    success_metrics=json.loads(row[6]) if row[6] else {}
                )
                self.learning_examples.append(example)
            
            # Load response patterns
            cursor = conn.execute("SELECT * FROM response_patterns")
            for row in cursor.fetchall():
                pattern = ResponsePattern(
                    pattern_id=row[0],
                    input_features=json.loads(row[1]),
                    response_template=row[2],
                    success_rate=row[3],
                    usage_count=row[4],
                    last_updated=row[5],
                    confidence_score=row[6]
                )
                self.response_patterns[pattern.pattern_id] = pattern
            
            # Load user preferences
            cursor = conn.execute("SELECT * FROM user_preferences")
            for row in cursor.fetchall():
                contact, key, value, confidence, last_updated = row
                self.user_preferences[contact][key] = {
                    'value': value,
                    'confidence': confidence,
                    'last_updated': last_updated
                }
    
    def add_learning_example(self, input_text: str, response_text: str,
                           user_feedback: float = None, context: Dict = None,
                           contact: str = "Unknown", success_metrics: Dict = None):
        """Add a new learning example"""
        example = LearningExample(
            input_text=input_text,
            response_text=response_text,
            user_feedback=user_feedback or 0.0,
            context=context or {},
            timestamp=datetime.utcnow().isoformat(),
            contact=contact,
            success_metrics=success_metrics or {}
        )
        
        self.learning_examples.append(example)
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO learning_examples 
                (input_text, response_text, user_feedback, context, timestamp, contact, success_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                example.input_text,
                example.response_text,
                example.user_feedback,
                json.dumps(example.context),
                example.timestamp,
                example.contact,
                json.dumps(example.success_metrics)
            ))
        
        # Trigger learning if we have enough examples
        if len(self.learning_examples) % 10 == 0:
            self._update_patterns()
    
    def _update_patterns(self):
        """Update response patterns based on learning examples"""
        if len(self.learning_examples) < self.min_examples_for_pattern:
            return
        
        # Extract features from all examples
        texts = [ex.input_text for ex in self.learning_examples]
        if not self.feature_extractor.is_fitted:
            self.feature_extractor.fit_tfidf(texts)
        
        # Group similar inputs
        feature_vectors = []
        for text in texts:
            tfidf_features = self.feature_extractor.get_tfidf_features(text)
            manual_features = list(self.feature_extractor.extract_features(text).values())
            combined_features = np.concatenate([tfidf_features, manual_features])
            feature_vectors.append(combined_features)
        
        # Cluster similar inputs
        if len(feature_vectors) >= self.min_examples_for_pattern:
            n_clusters = min(10, len(feature_vectors) // self.min_examples_for_pattern)
            if n_clusters > 1:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                clusters = kmeans.fit_predict(feature_vectors)
                
                # Create patterns for each cluster
                for cluster_id in range(n_clusters):
                    cluster_examples = [ex for i, ex in enumerate(self.learning_examples) 
                                      if clusters[i] == cluster_id]
                    
                    if len(cluster_examples) >= self.min_examples_for_pattern:
                        self._create_pattern_from_cluster(cluster_examples, cluster_id)
    
    def _create_pattern_from_cluster(self, examples: List[LearningExample], cluster_id: int):
        """Create a response pattern from a cluster of examples"""
        # Calculate success rate
        feedback_scores = [ex.user_feedback for ex in examples if ex.user_feedback is not None]
        success_rate = np.mean([1 if score > 0 else 0 for score in feedback_scores]) if feedback_scores else 0.5
        
        # Find most common response characteristics
        response_lengths = [len(ex.response_text) for ex in examples]
        avg_response_length = np.mean(response_lengths)
        
        # Extract common features
        input_features = []
        for ex in examples:
            features = self.feature_extractor.extract_features(ex.input_text, ex.context)
            input_features.append(features)
        
        # Create pattern
        pattern_id = f"pattern_{cluster_id}_{int(datetime.utcnow().timestamp())}"
        
        # Generate response template based on successful examples
        successful_examples = [ex for ex in examples if ex.user_feedback and ex.user_feedback > 0]
        if successful_examples:
            # Use the most successful response as template
            best_example = max(successful_examples, key=lambda x: x.user_feedback)
            response_template = best_example.response_text
        else:
            # Use most common response
            response_template = max(examples, key=lambda x: len(x.response_text)).response_text
        
        pattern = ResponsePattern(
            pattern_id=pattern_id,
            input_features=self._summarize_features(input_features),
            response_template=response_template,
            success_rate=success_rate,
            usage_count=len(examples),
            last_updated=datetime.utcnow().isoformat(),
            confidence_score=min(success_rate + 0.1, 1.0)
        )
        
        self.response_patterns[pattern_id] = pattern
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO response_patterns
                (pattern_id, input_features, response_template, success_rate, 
                 usage_count, last_updated, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                json.dumps(pattern.input_features),
                pattern.response_template,
                pattern.success_rate,
                pattern.usage_count,
                pattern.last_updated,
                pattern.confidence_score
            ))
    
    def _summarize_features(self, feature_list: List[List]) -> List[str]:
        """Summarize features from multiple examples"""
        if not feature_list:
            return []

        # Find common characteristics
        summary = []

        # Average numerical features
        num_features = len(feature_list[0]) if feature_list else 0
        for i in range(num_features):
            values = [f[i] for f in feature_list]
            avg_value = np.mean(values)
            if avg_value > 0:
                summary.append(f"feature_{i}:{avg_value:.1f}")

        return summary
    
    def get_response_suggestion(self, input_text: str, context: Dict = None,
                              contact: str = "Unknown") -> Optional[str]:
        """Get response suggestion based on learned patterns"""
        if not self.response_patterns:
            return None
        
        # Extract features from input
        features = self.feature_extractor.extract_features(input_text, context)
        
        # Find best matching pattern
        best_pattern = None
        best_score = 0
        
        for pattern in self.response_patterns.values():
            if pattern.confidence_score < self.pattern_confidence_threshold:
                continue
            
            # Calculate similarity score
            score = self._calculate_pattern_similarity(features, pattern)
            
            # Adjust score based on user preferences
            if contact in self.user_preferences:
                user_prefs = self.user_preferences[contact]
                if 'response_style' in user_prefs:
                    # Adjust score based on user's preferred response style
                    score *= user_prefs['response_style']['confidence']
            
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        if best_pattern and best_score > 0.5:
            # Update usage count
            best_pattern.usage_count += 1
            return best_pattern.response_template
        
        return None
    
    def _calculate_pattern_similarity(self, features: List, pattern: ResponsePattern) -> float:
        """Calculate similarity between input features and pattern"""
        # Use cosine similarity
        pattern_features = np.array(json.loads(pattern.input_features))
        input_features = np.array(features)

        if len(pattern_features) == 0 or len(input_features) == 0:
            return 0.0

        # Pad the shorter array with zeros to match the length of the longer array
        if len(pattern_features) < len(input_features):
            pattern_features = np.pad(pattern_features, (0, len(input_features) - len(pattern_features)), 'constant')
        elif len(input_features) < len(pattern_features):
            input_features = np.pad(input_features, (0, len(pattern_features) - len(input_features)), 'constant')

        similarity = cosine_similarity(input_features.reshape(1, -1), pattern_features.reshape(1, -1))[0][0]
        return similarity
    
    def update_user_preference(self, contact: str, preference_key: str,
                             preference_value: str, confidence: float = 0.8):
        """Update user preference based on interactions"""
        self.user_preferences[contact][preference_key] = {
            'value': preference_value,
            'confidence': confidence,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences
                (contact, preference_key, preference_value, confidence, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (
                contact,
                preference_key,
                preference_value,
                confidence,
                datetime.utcnow().isoformat()
            ))
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        recent_examples = [ex for ex in self.learning_examples if
                          datetime.fromisoformat(ex.timestamp) > datetime.utcnow() - timedelta(days=7)]

        # Calculate feedback distribution
        feedback_scores = [ex.user_feedback for ex in self.learning_examples if ex.user_feedback is not None]
        positive_feedback = len([f for f in feedback_scores if f > 0])
        negative_feedback = len([f for f in feedback_scores if f < 0])

        # Calculate pattern effectiveness
        effective_patterns = [p for p in self.response_patterns.values() if p.success_rate > 0.7]

        return {
            "total_examples": len(self.learning_examples),
            "total_patterns": len(self.response_patterns),
            "users_with_preferences": len(self.user_preferences),
            "avg_pattern_success_rate": np.mean([p.success_rate for p in self.response_patterns.values()]) if self.response_patterns else 0,
            "high_confidence_patterns": len([p for p in self.response_patterns.values() if p.confidence_score > 0.8]),
            "effective_patterns": len(effective_patterns),
            "recent_examples": len(recent_examples),
            "positive_feedback_ratio": positive_feedback / len(feedback_scores) if feedback_scores else 0,
            "negative_feedback_ratio": negative_feedback / len(feedback_scores) if feedback_scores else 0,
            "learning_velocity": len(recent_examples) / 7 if recent_examples else 0,  # Examples per day
            "pattern_diversity": len(set(p.response_template[:50] for p in self.response_patterns.values())),
            "user_engagement": len(set(ex.contact for ex in self.learning_examples))
        }

    def get_personalized_recommendations(self, contact: str, input_text: str) -> Dict[str, Any]:
        """Get personalized response recommendations for a user"""
        user_examples = [ex for ex in self.learning_examples if ex.contact == contact]

        if not user_examples:
            return {"recommendations": [], "confidence": 0.0, "reason": "No user history"}

        # Analyze user preferences
        positive_examples = [ex for ex in user_examples if ex.user_feedback and ex.user_feedback > 0]

        recommendations = []

        if positive_examples:
            # Find common patterns in successful responses
            successful_features = []
            for ex in positive_examples:
                features = self.feature_extractor.extract_features(ex.response_text)
                successful_features.append(features)

            # Calculate average successful response characteristics
            avg_length = np.mean([f['length'] for f in successful_features])
            avg_emoji_count = np.mean([f['emoji_count'] for f in successful_features])

            recommendations.append({
                "type": "response_style",
                "suggestion": f"Keep responses around {int(avg_length)} characters",
                "confidence": 0.8
            })

            if avg_emoji_count > 0.5:
                recommendations.append({
                    "type": "emoji_usage",
                    "suggestion": "User prefers responses with emojis",
                    "confidence": 0.7
                })

        # Analyze conversation patterns
        recent_examples = [ex for ex in user_examples if
                          datetime.fromisoformat(ex.timestamp) > datetime.utcnow() - timedelta(days=30)]

        if recent_examples:
            common_topics = {}
            for ex in recent_examples:
                # Simple topic extraction based on keywords
                words = ex.input_text.lower().split()
                for word in words:
                    if len(word) > 4:  # Focus on meaningful words
                        common_topics[word] = common_topics.get(word, 0) + 1

            if common_topics:
                top_topic = max(common_topics, key=common_topics.get)
                recommendations.append({
                    "type": "topic_preference",
                    "suggestion": f"User frequently discusses: {top_topic}",
                    "confidence": 0.6
                })

        return {
            "recommendations": recommendations,
            "confidence": len(recommendations) * 0.2,
            "user_examples_count": len(user_examples),
            "positive_examples_count": len(positive_examples)
        }

# Global adaptive learning system instance
_adaptive_learning_system = None

def get_adaptive_learning_system() -> AdaptiveLearningSystem:
    """Get global adaptive learning system instance"""
    global _adaptive_learning_system
    if _adaptive_learning_system is None:
        _adaptive_learning_system = AdaptiveLearningSystem()
    return _adaptive_learning_system
