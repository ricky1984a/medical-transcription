"""
Schema definitions for request validation
"""
from marshmallow import Schema, fields, validate, ValidationError, validates_schema


class UserSchema(Schema):
    """Schema for user registration and updates"""
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=12))

    @validates_schema
    def validate_password_strength(self, data, **kwargs):
        """Validate password strength"""
        if 'password' in data:
            password = data['password']

            # Check for complexity requirements
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(not c.isalnum() for c in password)

            if not (has_upper and has_lower and has_digit and has_special):
                raise ValidationError(
                    "Password must contain uppercase, lowercase, digit, and special characters",
                    field_name="password"
                )


class LoginSchema(Schema):
    """Schema for login requests"""
    username = fields.Str(required=True)  # This is actually the email
    password = fields.Str(required=True)


class TranscriptionSchema(Schema):
    """Schema for transcription creation and updates"""
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    language = fields.Str(required=False, validate=validate.Length(min=2, max=10))
    content = fields.Str(required=False)
    status = fields.Str(
        required=False,
        validate=validate.OneOf(['pending', 'processing', 'completed', 'failed', 'no_speech_detected'])
    )


class TranslationSchema(Schema):
    """Schema for translation requests"""
    transcription_id = fields.Int(required=False)
    text = fields.Str(required=False)
    source_language = fields.Str(required=False, validate=validate.Length(min=2, max=10))
    target_language = fields.Str(required=True, validate=validate.Length(min=2, max=10))
    high_quality = fields.Bool(required=False, default=True)

    @validates_schema
    def validate_source_required(self, data, **kwargs):
        """Validate that either transcription_id or text is provided"""
        if not data.get('transcription_id') and not data.get('text'):
            raise ValidationError(
                "Either transcription_id or text must be provided",
                field_name="transcription_id"
            )


class TranscriptionAnalysisSchema(Schema):
    """Schema for transcription analysis requests"""
    transcription_id = fields.Int(required=True)


class RefreshTokenSchema(Schema):
    """Schema for token refresh requests"""
    refresh_token = fields.Str(required=True)


class FileUploadSchema(Schema):
    """Schema for file upload metadata"""
    language = fields.Str(required=False, validate=validate.Length(min=2, max=10))
    analyze = fields.Bool(required=False, default=False)
    quality = fields.Str(
        required=False,
        validate=validate.OneOf(['low', 'medium', 'high']),
        default='medium'
    )