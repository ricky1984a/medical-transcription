"""
Transcription model for storing transcription data
"""
from datetime import datetime
from ..db import db


class Transcription(db.Model):
    """Model for storing transcriptions of audio files"""
    __tablename__ = 'transcriptions'

    # Add extend_existing=True to prevent table redefinition errors
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(10), default='en')
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationship to user
    user = db.relationship('User', backref=db.backref('transcriptions', lazy=True))

    def __repr__(self):
        return f"<Transcription {self.id}: {self.title}>"

    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'user_id': self.user_id,
            'file_path': self.file_path,
            'language': self.language,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }