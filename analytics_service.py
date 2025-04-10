"""
Analytics service module for collecting and reporting chatbot performance metrics.
This module provides functions to:
1. Track chat sessions and interactions
2. Generate performance summaries and reports
3. Provide data for the analytics dashboard
"""

import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, extract
from database_service import db_session
from models import (
    ChatSession, ChatInteraction, AnalyticsSummary, 
    User, Product, Order
)

logger = logging.getLogger(__name__)

# Session Tracking Functions

def create_chat_session(session_id, user_id=None, platform="web", device_info=None):
    """
    Create a new chat session record.
    Returns the created session.
    """
    try:
        session = db_session()
        
        # Check if session already exists
        existing_session = session.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if existing_session:
            logger.info(f"Chat session {session_id} already exists")
            session.close()
            return existing_session
        
        # Create new session
        chat_session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            platform=platform,
            device_info=device_info
        )
        
        session.add(chat_session)
        session.commit()
        logger.info(f"Created new chat session: {session_id}")
        
        # Return a copy of the session data before closing the db session
        result = chat_session.to_dict()
        session.close()
        return result
    
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}", exc_info=True)
        session.rollback()
        session.close()
        return None

def end_chat_session(session_id):
    """
    Mark a chat session as ended and record the end time.
    Returns the updated session data.
    """
    try:
        session = db_session()
        
        chat_session = session.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            logger.warning(f"Chat session {session_id} not found for ending")
            session.close()
            return None
        
        # Only update if not already ended
        if not chat_session.end_time:
            chat_session.end_time = datetime.utcnow()
            session.commit()
            logger.info(f"Ended chat session: {session_id}")
        
        # Return a copy of the session data before closing the db session
        result = chat_session.to_dict()
        session.close()
        return result
    
    except Exception as e:
        logger.error(f"Error ending chat session: {str(e)}", exc_info=True)
        session.rollback()
        session.close()
        return None

def record_chat_interaction(session_id, user_message, chatbot_response=None, 
                          detected_intent=None, confidence_score=None, 
                          has_attachment=False, attachment_type=None,
                          response_time_ms=None, products_shown=0, 
                          entities=None, sentiment_score=None, 
                          was_successful=True, error_type=None):
    """
    Record a chat interaction between user and chatbot.
    Returns the created interaction data.
    """
    try:
        session = db_session()
        
        # Ensure session exists
        chat_session = session.query(ChatSession).filter(
            ChatSession.session_id == session_id
        ).first()
        
        if not chat_session:
            # Create session if it doesn't exist
            logger.warning(f"Chat session {session_id} not found, creating now")
            new_session = ChatSession(session_id=session_id)
            session.add(new_session)
            session.commit()
        
        # Create interaction
        interaction = ChatInteraction(
            session_id=session_id,
            user_message=user_message,
            chatbot_response=chatbot_response,
            detected_intent=detected_intent,
            confidence_score=confidence_score,
            has_attachment=has_attachment,
            attachment_type=attachment_type,
            response_time_ms=response_time_ms,
            products_shown=products_shown,
            entities=entities,
            sentiment_score=sentiment_score,
            was_successful=was_successful,
            error_type=error_type
        )
        
        session.add(interaction)
        session.commit()
        logger.info(f"Recorded chat interaction in session {session_id}")
        
        # Return a copy of the interaction data before closing the db session
        result = interaction.to_dict()
        session.close()
        return result
    
    except Exception as e:
        logger.error(f"Error recording chat interaction: {str(e)}", exc_info=True)
        session.rollback()
        session.close()
        return None

# Analytics Report Functions

def generate_daily_summary(date=None):
    """
    Generate or update the daily analytics summary for a given date.
    If date is None, generates for the current day.
    Returns the summary data.
    """
    if date is None:
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    try:
        session = db_session()
        
        # Check if summary already exists
        existing_summary = session.query(AnalyticsSummary).filter(
            AnalyticsSummary.date == date,
            AnalyticsSummary.period_type == 'daily'
        ).first()
        
        if not existing_summary:
            # Create new summary
            summary = AnalyticsSummary(date=date, period_type='daily')
            session.add(summary)
        else:
            summary = existing_summary
        
        # Define the date range for the summary (00:00:00 to 23:59:59)
        start_date = date
        end_date = date + timedelta(days=1) - timedelta(microseconds=1)
        
        # Get basic metrics for the day
        total_sessions = session.query(func.count(ChatSession.id)).filter(
            ChatSession.start_time >= start_date,
            ChatSession.start_time <= end_date
        ).scalar() or 0
        
        total_interactions = session.query(func.count(ChatInteraction.id)).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date
        ).scalar() or 0
        
        unique_users = session.query(func.count(func.distinct(ChatSession.user_id))).filter(
            ChatSession.start_time >= start_date,
            ChatSession.start_time <= end_date,
            ChatSession.user_id != None
        ).scalar() or 0
        
        # Calculate average session duration
        avg_duration = session.query(
            func.avg(
                func.extract('epoch', ChatSession.end_time) - 
                func.extract('epoch', ChatSession.start_time)
            )
        ).filter(
            ChatSession.start_time >= start_date,
            ChatSession.start_time <= end_date,
            ChatSession.end_time != None
        ).scalar()
        
        # Calculate average response time
        avg_response_time = session.query(
            func.avg(ChatInteraction.response_time_ms)
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date,
            ChatInteraction.response_time_ms != None
        ).scalar()
        
        # Count product metrics
        products_shown = session.query(
            func.sum(ChatInteraction.products_shown)
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date
        ).scalar() or 0
        
        product_search_count = session.query(
            func.count(ChatInteraction.id)
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date,
            ChatInteraction.detected_intent == 'product_search'
        ).scalar() or 0
        
        # Count errors
        error_count = session.query(
            func.count(ChatInteraction.id)
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date,
            ChatInteraction.was_successful == False
        ).scalar() or 0
        
        # Get intent distribution
        intent_counts = {}
        intent_results = session.query(
            ChatInteraction.detected_intent, 
            func.count(ChatInteraction.id)
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date,
            ChatInteraction.detected_intent != None
        ).group_by(ChatInteraction.detected_intent).all()
        
        for intent, count in intent_results:
            intent_counts[intent] = count
        
        # Get error distribution
        error_counts = {}
        error_results = session.query(
            ChatInteraction.error_type, 
            func.count(ChatInteraction.id)
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date,
            ChatInteraction.error_type != None
        ).group_by(ChatInteraction.error_type).all()
        
        for error_type, count in error_results:
            error_counts[error_type] = count
        
        # Get platform distribution
        platform_counts = {}
        platform_results = session.query(
            ChatSession.platform, 
            func.count(ChatSession.id)
        ).filter(
            ChatSession.start_time >= start_date,
            ChatSession.start_time <= end_date,
            ChatSession.platform != None
        ).group_by(ChatSession.platform).all()
        
        for platform, count in platform_results:
            platform_counts[platform] = count
        
        # Update summary object
        summary.total_sessions = total_sessions
        summary.total_interactions = total_interactions
        summary.unique_users = unique_users
        summary.avg_session_duration_seconds = avg_duration
        summary.avg_response_time_ms = avg_response_time
        summary.products_shown_count = products_shown
        summary.product_search_count = product_search_count
        summary.error_count = error_count
        summary.set_intent_distribution(intent_counts)
        summary.set_error_distribution(error_counts)
        summary.set_platform_distribution(platform_counts)
        
        session.commit()
        
        # Return a dictionary representation
        result = {
            'date': date.isoformat(),
            'period_type': 'daily',
            'total_sessions': total_sessions,
            'total_interactions': total_interactions,
            'unique_users': unique_users,
            'avg_session_duration_seconds': avg_duration,
            'avg_response_time_ms': avg_response_time,
            'products_shown_count': products_shown,
            'product_search_count': product_search_count,
            'error_count': error_count,
            'intent_distribution': intent_counts,
            'error_distribution': error_counts,
            'platform_distribution': platform_counts
        }
        
        session.close()
        return result
    
    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}", exc_info=True)
        if 'session' in locals():
            session.rollback()
            session.close()
        return None

def get_dashboard_summary(days=7):
    """
    Get summary data for the dashboard, covering the last N days.
    Returns aggregated metrics and trends.
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        session = db_session()
        
        # Get daily summaries for the period
        daily_summaries = session.query(AnalyticsSummary).filter(
            AnalyticsSummary.date >= start_date,
            AnalyticsSummary.date <= end_date,
            AnalyticsSummary.period_type == 'daily'
        ).order_by(AnalyticsSummary.date).all()
        
        # Ensure we have summaries for all days in the range
        existing_dates = set(summary.date.date() for summary in daily_summaries)
        date_range = [start_date.date() + timedelta(days=i) for i in range(days)]
        
        missing_dates = [d for d in date_range if d not in existing_dates]
        
        # Generate missing summaries
        for missing_date in missing_dates:
            generate_daily_summary(
                datetime(missing_date.year, missing_date.month, missing_date.day)
            )
        
        # Reload if we generated new summaries
        if missing_dates:
            daily_summaries = session.query(AnalyticsSummary).filter(
                AnalyticsSummary.date >= start_date,
                AnalyticsSummary.date <= end_date,
                AnalyticsSummary.period_type == 'daily'
            ).order_by(AnalyticsSummary.date).all()
        
        # Calculate period totals
        total_sessions = sum(summary.total_sessions for summary in daily_summaries)
        total_interactions = sum(summary.total_interactions for summary in daily_summaries)
        total_products_shown = sum(summary.products_shown_count for summary in daily_summaries)
        total_errors = sum(summary.error_count for summary in daily_summaries)
        
        # Calculate averages
        avg_session_duration = sum(
            summary.avg_session_duration_seconds or 0 for summary in daily_summaries
        ) / (len(daily_summaries) or 1)
        
        avg_response_time = sum(
            summary.avg_response_time_ms or 0 for summary in daily_summaries
        ) / (len(daily_summaries) or 1)
        
        # Combine intent distributions
        intent_distribution = {}
        for summary in daily_summaries:
            for intent, count in summary.get_intent_distribution().items():
                if intent in intent_distribution:
                    intent_distribution[intent] += count
                else:
                    intent_distribution[intent] = count
        
        # Prepare daily trend data
        trend_data = []
        for summary in daily_summaries:
            trend_data.append({
                'date': summary.date.strftime('%Y-%m-%d'),
                'sessions': summary.total_sessions,
                'interactions': summary.total_interactions,
                'avg_duration': summary.avg_session_duration_seconds or 0,
                'avg_response_time': summary.avg_response_time_ms or 0,
                'error_count': summary.error_count
            })
        
        # Add top products (most frequently shown in interactions)
        top_products_query = session.query(
            ChatInteraction.entities,
            func.count(ChatInteraction.id).label('count')
        ).filter(
            ChatInteraction.timestamp >= start_date,
            ChatInteraction.timestamp <= end_date,
            ChatInteraction.entities != None,
            ChatInteraction.products_shown > 0
        ).group_by(ChatInteraction.entities).order_by(desc('count')).limit(5).all()
        
        top_products = []
        for entity_json, count in top_products_query:
            try:
                entities = json.loads(entity_json)
                if 'product' in entities:
                    top_products.append({
                        'product': entities['product'],
                        'count': count
                    })
            except:
                pass
        
        dashboard_data = {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'days': days
            },
            'totals': {
                'sessions': total_sessions,
                'interactions': total_interactions,
                'products_shown': total_products_shown,
                'errors': total_errors
            },
            'averages': {
                'session_duration_seconds': avg_session_duration,
                'response_time_ms': avg_response_time,
                'interactions_per_session': (
                    total_interactions / total_sessions if total_sessions else 0
                )
            },
            'intent_distribution': intent_distribution,
            'daily_trends': trend_data,
            'top_products': top_products
        }
        
        session.close()
        return dashboard_data
    
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}", exc_info=True)
        if 'session' in locals():
            session.rollback()
            session.close()
        return None

def get_recent_chat_sessions(limit=10):
    """
    Get the most recent chat sessions with their interaction counts.
    """
    try:
        session = db_session()
        
        # Get recent sessions with interaction counts
        query = session.query(
            ChatSession,
            func.count(ChatInteraction.id).label('interaction_count')
        ).outerjoin(
            ChatInteraction, 
            ChatSession.session_id == ChatInteraction.session_id
        ).group_by(
            ChatSession
        ).order_by(
            desc(ChatSession.start_time)
        ).limit(limit)
        
        results = query.all()
        
        recent_sessions = []
        for chat_session, interaction_count in results:
            session_data = chat_session.to_dict()
            session_data['interaction_count'] = interaction_count
            
            # Get the user name if available
            if chat_session.user_id:
                user = session.query(User).filter(
                    User.user_id == chat_session.user_id
                ).first()
                if user:
                    session_data['user_name'] = user.name
            
            recent_sessions.append(session_data)
        
        session.close()
        return recent_sessions
    
    except Exception as e:
        logger.error(f"Error getting recent chat sessions: {str(e)}", exc_info=True)
        if 'session' in locals():
            session.rollback()
            session.close()
        return []