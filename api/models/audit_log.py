"""
Audit log model for HIPAA compliance
"""
import logging
from datetime import datetime
from flask import request, has_request_context
from ..db import db

logger = logging.getLogger(__name__)


class AuditLog(db.Model):
    """Model for tracking PHI access for HIPAA compliance"""
    __tablename__ = 'audit_logs'

    # Add extend_existing=True to prevent table redefinition errors
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Define relationship to user
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.user_id} {self.action} {self.resource_type} {self.resource_id}>"

    @classmethod
    def log_phi_access(cls, user_id, resource_type, resource_id, action, description=None):
        """
        Log access to Protected Health Information (PHI)

        Args:
            user_id: ID of the user accessing the data (0 for system actions)
            resource_type: Type of resource being accessed (e.g., 'transcription')
            resource_id: ID of the resource
            action: Action being performed (e.g., 'view', 'update', 'delete')
            description: Optional description of the access

        Returns:
            AuditLog: The created audit log entry
        """
        # Get IP and user agent if in request context
        ip_address = None
        user_agent = None

        if has_request_context():
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else None

        try:
            # Create log entry
            log_entry = cls(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent
            )

            db.session.add(log_entry)
            db.session.commit()

            logger.info(
                f"Audit log: User {user_id} performed {action} on {resource_type} {resource_id}"
            )

            return log_entry

        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            db.session.rollback()

            # If database logging fails, at least log to application logs
            logger.warning(
                f"PHI ACCESS: User {user_id} performed {action} on {resource_type} {resource_id}"
            )

            return None

    @classmethod
    def search(cls, user_id=None, resource_type=None, resource_id=None, action=None,
               start_date=None, end_date=None, limit=100):
        """
        Search audit logs with filters

        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            action: Filter by action
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results to return

        Returns:
            list: Filtered audit logs
        """
        query = cls.query

        if user_id is not None:
            query = query.filter(cls.user_id == user_id)

        if resource_type is not None:
            query = query.filter(cls.resource_type == resource_type)

        if resource_id is not None:
            query = query.filter(cls.resource_id == resource_id)

        if action is not None:
            query = query.filter(cls.action == action)

        if start_date is not None:
            query = query.filter(cls.timestamp >= start_date)

        if end_date is not None:
            query = query.filter(cls.timestamp <= end_date)

        # Order by timestamp descending (newest first)
        query = query.order_by(cls.timestamp.desc())

        # Limit results
        query = query.limit(limit)

        return query.all()