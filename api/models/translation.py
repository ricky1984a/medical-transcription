"""
Translation model for storing translation data
"""
from datetime import datetime
from ..db import db


class Translation(db.Model):
    """Model for storing translations of transcriptions"""
    __tablename__ = 'translations'

    # Add extend_existing=True to prevent table redefinition errors
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    transcription_id = db.Column(db.Integer, db.ForeignKey('transcriptions.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    source_language = db.Column(db.String(10), nullable=False)
    target_language = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define relationship to transcription
    transcription = db.relationship('Transcription', backref=db.backref('translations', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Translation {self.id}: {self.source_language} to {self.target_language}>"

    def to_dict(self):
        """Convert model to dictionary for API responses"""
        return {
            'id': self.id,
            'transcription_id': self.transcription_id,
            'content': self.content,
            'source_language': self.source_language,
            'target_language': self.target_language,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }