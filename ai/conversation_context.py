#!/usr/bin/env python3
"""
Advanced Conversation Context Management
Handles multi-turn conversations, context awareness, and personality consistency.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import os

@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation"""
    timestamp: str
    incoming: str
    response: str
    sentiment: str
    intent: str
    confidence: float
    context_used: List[str]
    user_feedback: Optional[str] = None

@dataclass
class PersonalityProfile:
    """AI personality configuration"""
    name: str
    base_traits: List[str]  # e.g., ["friendly", "professional", "humorous"]
    communication_style: str  # "formal", "casual", "enthusiastic", etc.
    response_length_preference: str  # "brief", "moderate", "detailed"
    emoji_usage: str  # "none", "minimal", "moderate", "frequent"
    topics_of_interest: List[str]
    topics_to_avoid: List[str]
    custom_phrases: List[str]
    relationship_context: Dict[str, str]  # contact -> relationship type

class ConversationContextManager:
    """Manages conversation context and personality consistency"""
    
    def __init__(self, data_dir: str = "dayle_data"):
        self.data_dir = data_dir
        self.context_dir = os.path.join(data_dir, "conversations")
        self.personality_dir = os.path.join(data_dir, "personalities")
        os.makedirs(self.context_dir, exist_ok=True)
        os.makedirs(self.personality_dir, exist_ok=True)
        
        # Context retention settings
        self.max_context_turns = 10
        self.context_decay_hours = 24
        self.relevance_threshold = 0.3
    
    def get_conversation_file(self, contact: str) -> str:
        """Get conversation file path for contact"""
        safe_contact = contact.lower().replace("/", "_").replace(" ", "_")
        return os.path.join(self.context_dir, f"{safe_contact}_context.json")
    
    def load_conversation_context(self, contact: str) -> List[ConversationTurn]:
        """Load conversation history for contact"""
        file_path = self.get_conversation_file(contact)
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return [ConversationTurn(**turn) for turn in data.get("turns", [])]
        except Exception as e:
            print(f"Error loading conversation context: {e}")
            return []
    
    def save_conversation_turn(self, contact: str, turn: ConversationTurn):
        """Save a conversation turn"""
        file_path = self.get_conversation_file(contact)
        turns = self.load_conversation_context(contact)
        
        # Add new turn
        turns.append(turn)
        
        # Cleanup old turns
        turns = self._cleanup_old_turns(turns)
        
        # Save to file
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    "contact": contact,
                    "last_updated": datetime.utcnow().isoformat(),
                    "turns": [asdict(turn) for turn in turns]
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving conversation turn: {e}")
    
    def _cleanup_old_turns(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        """Remove old or irrelevant turns"""
        if not turns:
            return turns
        
        # Remove turns older than decay period
        cutoff_time = datetime.utcnow() - timedelta(hours=self.context_decay_hours)
        recent_turns = []
        
        for turn in turns:
            try:
                turn_time = datetime.fromisoformat(turn.timestamp.replace('Z', '+00:00'))
                if turn_time > cutoff_time:
                    recent_turns.append(turn)
            except:
                # Keep turn if we can't parse timestamp
                recent_turns.append(turn)
        
        # Keep only most recent turns
        return recent_turns[-self.max_context_turns:]
    
    def get_relevant_context(self, contact: str, current_message: str, max_turns: int = 5) -> List[ConversationTurn]:
        """Get contextually relevant conversation history"""
        turns = self.load_conversation_context(contact)
        if not turns:
            return []
        
        # For now, return most recent turns
        # TODO: Implement semantic similarity matching
        return turns[-max_turns:]
    
    def build_context_prompt(self, contact: str, current_message: str, personality: Optional[PersonalityProfile] = None) -> str:
        """Build context-aware prompt for AI"""
        context_turns = self.get_relevant_context(contact, current_message)
        
        prompt_parts = []
        
        # Add personality context
        if personality:
            prompt_parts.append(f"You are {personality.name}, with these traits: {', '.join(personality.base_traits)}")
            prompt_parts.append(f"Communication style: {personality.communication_style}")
            prompt_parts.append(f"Response length: {personality.response_length_preference}")
            
            if contact in personality.relationship_context:
                relationship = personality.relationship_context[contact]
                prompt_parts.append(f"Your relationship with {contact}: {relationship}")
        
        # Add conversation history
        if context_turns:
            prompt_parts.append("\nRecent conversation history:")
            for turn in context_turns[-3:]:  # Last 3 turns
                prompt_parts.append(f"Them: {turn.incoming}")
                prompt_parts.append(f"You: {turn.response}")
        
        prompt_parts.append(f"\nCurrent message from {contact}: {current_message}")
        prompt_parts.append("\nRespond naturally, maintaining consistency with your personality and conversation history.")
        
        return "\n".join(prompt_parts)
    
    def load_personality(self, personality_name: str = "default") -> Optional[PersonalityProfile]:
        """Load personality profile"""
        file_path = os.path.join(self.personality_dir, f"{personality_name}.json")
        if not os.path.exists(file_path):
            return self._create_default_personality()
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return PersonalityProfile(**data)
        except Exception as e:
            print(f"Error loading personality: {e}")
            return self._create_default_personality()
    
    def save_personality(self, personality: PersonalityProfile):
        """Save personality profile"""
        file_path = os.path.join(self.personality_dir, f"{personality.name}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(asdict(personality), f, indent=2)
        except Exception as e:
            print(f"Error saving personality: {e}")
    
    def _create_default_personality(self) -> PersonalityProfile:
        """Create default personality profile"""
        return PersonalityProfile(
            name="default",
            base_traits=["helpful", "friendly", "concise"],
            communication_style="casual",
            response_length_preference="brief",
            emoji_usage="minimal",
            topics_of_interest=["general conversation", "helping with tasks"],
            topics_to_avoid=["controversial topics", "personal information"],
            custom_phrases=["Happy to help!", "Let me know if you need anything else"],
            relationship_context={}
        )
    
    def analyze_conversation_patterns(self, contact: str) -> Dict[str, Any]:
        """Analyze conversation patterns for insights"""
        turns = self.load_conversation_context(contact)
        if not turns:
            return {"error": "No conversation history"}
        
        # Basic analytics
        total_turns = len(turns)
        sentiments = [turn.sentiment for turn in turns if turn.sentiment]
        intents = [turn.intent for turn in turns if turn.intent]
        avg_confidence = sum(turn.confidence for turn in turns if turn.confidence) / len(turns)
        
        # Response time analysis
        response_lengths = [len(turn.response) for turn in turns]
        avg_response_length = sum(response_lengths) / len(response_lengths)
        
        return {
            "total_conversations": total_turns,
            "sentiment_distribution": {s: sentiments.count(s) for s in set(sentiments)},
            "intent_distribution": {i: intents.count(i) for i in set(intents)},
            "average_confidence": avg_confidence,
            "average_response_length": avg_response_length,
            "conversation_span_days": self._calculate_conversation_span(turns),
            "most_recent_activity": turns[-1].timestamp if turns else None
        }
    
    def _calculate_conversation_span(self, turns: List[ConversationTurn]) -> float:
        """Calculate span of conversation in days"""
        if len(turns) < 2:
            return 0
        
        try:
            first = datetime.fromisoformat(turns[0].timestamp.replace('Z', '+00:00'))
            last = datetime.fromisoformat(turns[-1].timestamp.replace('Z', '+00:00'))
            return (last - first).days
        except:
            return 0
    
    def get_conversation_summary(self, contact: str, max_turns: int = 20) -> str:
        """Generate a summary of recent conversation"""
        turns = self.load_conversation_context(contact)[-max_turns:]
        if not turns:
            return "No recent conversation history."
        
        # Simple summary - could be enhanced with AI summarization
        topics = []
        sentiments = []
        
        for turn in turns:
            if turn.intent and turn.intent not in ["acknowledge", "other"]:
                topics.append(turn.intent)
            if turn.sentiment:
                sentiments.append(turn.sentiment)
        
        summary_parts = []
        summary_parts.append(f"Recent conversation with {contact}:")
        summary_parts.append(f"- {len(turns)} exchanges over {self._calculate_conversation_span(turns)} days")
        
        if topics:
            common_topics = list(set(topics))[:3]
            summary_parts.append(f"- Main topics: {', '.join(common_topics)}")
        
        if sentiments:
            positive_ratio = sentiments.count("positive") / len(sentiments)
            if positive_ratio > 0.6:
                summary_parts.append("- Generally positive tone")
            elif positive_ratio < 0.3:
                summary_parts.append("- Some negative sentiment detected")
            else:
                summary_parts.append("- Mixed sentiment")
        
        return "\n".join(summary_parts)

# Global context manager instance
_context_manager = None

def get_context_manager() -> ConversationContextManager:
    """Get global context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ConversationContextManager()
    return _context_manager
