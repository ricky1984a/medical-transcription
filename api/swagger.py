"""
Swagger API documentation setup for the medical transcription app
"""
from flask import Blueprint, jsonify, render_template
from flask_swagger_ui import get_swaggerui_blueprint
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from .config import config

# Initialize blueprint for serving the OpenAPI specification
swagger_bp = Blueprint('swagger', __name__, url_prefix='/api')

# Get Swagger config from app config
swagger_config = config.get_swagger_config()

# Create an APISpec
spec = APISpec(
    title=swagger_config.get('title', "Medical Transcription API"),
    version=swagger_config.get('version', "1.0.0"),
    openapi_version=swagger_config.get('openapi_version', "3.0.2"),
    info=dict(
        description=swagger_config.get('description', "API for medical audio transcription and translation"),
        contact=dict(email=swagger_config.get('contact_email', "ebenezerbrant44@gmail.com"))
    ),
    plugins=[MarshmallowPlugin()],
)

# Define security schemes
spec.components.security_scheme("BearerAuth", {
    "type": "http",
    "scheme": "bearer",
    "bearerFormat": "JWT"
})

# Define schemas
user_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "format": "int64", "description": "Unique identifier for the user"},
        "username": {"type": "string", "description": "Username for login"},
        "email": {"type": "string", "format": "email", "description": "User's email address"},
        "is_active": {"type": "boolean", "description": "Whether the user account is active"},
        "created_at": {"type": "string", "format": "date-time", "description": "When the user account was created"},
    },
    "required": ["id", "username", "email"],
    "example": {
        "id": 1,
        "username": "johnsmith",
        "email": "john@example.com",
        "is_active": True,
        "created_at": "2025-03-28T10:15:30Z"
    }
}

transcription_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "format": "int64", "description": "Unique identifier for the transcription"},
        "title": {"type": "string", "description": "Title of the transcription"},
        "content": {"type": "string", "description": "Transcribed text content"},
        "user_id": {"type": "integer", "format": "int64", "description": "ID of the user who owns this transcription"},
        "file_path": {"type": "string", "description": "Path to the stored audio file", "nullable": True},
        "language": {"type": "string", "description": "Language code of the transcription (ISO 639-1)"},
        "status": {
            "type": "string",
            "enum": ["pending", "processing", "completed", "failed"],
            "description": "Current status of the transcription process"
        },
        "created_at": {"type": "string", "format": "date-time", "description": "When the transcription was created"},
        "updated_at": {"type": "string", "format": "date-time",
                       "description": "When the transcription was last updated"}
    },
    "required": ["id", "title", "user_id", "status"],
    "example": {
        "id": 1,
        "title": "Medical Consultation",
        "content": "Doctor: How are you feeling today?\nPatient: I've been experiencing headaches.",
        "user_id": 5,
        "file_path": "/uploads/audio-1234.wav",
        "language": "en",
        "status": "completed",
        "created_at": "2025-03-30T10:15:30Z",
        "updated_at": "2025-03-30T10:20:45Z"
    }
}

translation_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "format": "int64", "description": "Unique identifier for the translation"},
        "transcription_id": {"type": "integer", "format": "int64", "description": "ID of the associated transcription"},
        "content": {"type": "string", "description": "Translated text content"},
        "source_language": {"type": "string", "description": "Source language code (ISO 639-1)"},
        "target_language": {"type": "string", "description": "Target language code (ISO 639-1)"},
        "status": {
            "type": "string",
            "enum": ["pending", "processing", "completed", "failed"],
            "description": "Current status of the translation process"
        },
        "created_at": {"type": "string", "format": "date-time", "description": "When the translation was created"},
        "updated_at": {"type": "string", "format": "date-time", "description": "When the translation was last updated"}
    },
    "required": ["id", "transcription_id", "source_language", "target_language", "status"],
    "example": {
        "id": 2,
        "transcription_id": 1,
        "content": "Doctor: ¿Cómo se siente hoy?\nPaciente: He estado experimentando dolores de cabeza.",
        "source_language": "en",
        "target_language": "es",
        "status": "completed",
        "created_at": "2025-03-30T10:25:30Z",
        "updated_at": "2025-03-30T10:26:45Z"
    }
}

# Common responses
unauthorized_response = {
    "description": "Unauthorized",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                }
            },
            "example": {
                "message": "Token is missing or invalid"
            }
        }
    }
}

not_found_response = {
    "description": "Not Found",
    "content": {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                }
            },
            "example": {
                "message": "Resource not found"
            }
        }
    }
}

# Register schemas with spec
spec.components.schema("User", user_schema)
spec.components.schema("AI - Transcription", transcription_schema)
spec.components.schema("AI - Translation", translation_schema)

# Add response components
spec.components.response("Unauthorized", unauthorized_response)
spec.components.response("NotFound", not_found_response)

# Add tag descriptions
spec.tag({
    "name": "Authentication",
    "description": "User registration and authentication operations"
})

spec.tag({
    "name": "Users",
    "description": "Operations related to user management"
})

# Add AI-related tags
spec.tag({
    "name": "AI - Transcriptions",
    "description": "AI-powered transcription enhancements"
})

spec.tag({
    "name": "AI - Translations",
    "description": "AI-powered translation enhancements"
})

# Define paths manually
paths = {
    "/api/register": {
        "post": {
            "tags": ["Authentication"],
            "summary": "Register a new user",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "email": {"type": "string", "format": "email"},
                                "password": {"type": "string", "format": "password"}
                            },
                            "required": ["username", "email", "password"]
                        }
                    }
                }
            },
            "responses": {
                "201": {
                    "description": "User registered successfully",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    }
                },
                "400": {
                    "description": "Bad Request",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"}
                                }
                            },
                            "example": {
                                "message": "Email already registered"
                            }
                        }
                    }
                }
            }
        }
    },
    "/api/token": {
        "post": {
            "tags": ["Authentication"],
            "summary": "Authenticate user and get token",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "username": {"type": "string"},
                                "password": {"type": "string", "format": "password"}
                            },
                            "required": ["username", "password"]
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Authentication successful",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "access_token": {"type": "string"},
                                    "token_type": {"type": "string"}
                                }
                            },
                            "example": {
                                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "token_type": "bearer"
                            }
                        }
                    }
                },
                "401": {"$ref": "#/components/responses/Unauthorized"}
            }
        }
    },
    "/api/users/me": {
        "get": {
            "tags": ["Users"],
            "summary": "Get current user profile",
            "security": [{"BearerAuth": []}],
            "responses": {
                "200": {
                    "description": "User profile retrieved successfully",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    }
                },
                "401": {"$ref": "#/components/responses/Unauthorized"}
            }
        }
    },
    "/api/ai/transcriptions/{transcription_id}/analysis": {
        "get": {
            "tags": ["AI - Transcriptions"],
            "summary": "Analyze transcription content with AI for medical coding",
            "description": "Uses AI to extract medical codes and relevant info from transcription content.",
            "security": [{"BearerAuth": []}],
            "parameters": [{
                "name": "transcription_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "ID of the transcription"
            }],
            "responses": {
                "200": {
                    "description": "Analysis completed",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "transcription_id": {"type": "integer"},
                                    "analysis": {"type": "object"}
                                }
                            }
                        }
                    }
                },
                "400": {"description": "Bad Request"},
                "404": {"description": "Not Found"},
                "503": {"description": "AI service unavailable"},
                "500": {"description": "AI analysis failed"}
            }
        }
    },
    "/api/ai/transcriptions/{transcription_id}/summarize": {
        "get": {
            "tags": ["AI - Transcriptions"],
            "summary": "Summarize transcription content using AI",
            "description": "Provides a concise summary of a transcription using AI.",
            "security": [{"BearerAuth": []}],
            "parameters": [{
                "name": "transcription_id",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
                "description": "ID of the transcription"
            }],
            "responses": {
                "200": {
                    "description": "Summary generated",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "transcription_id": {"type": "integer"},
                                    "summary": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "400": {"description": "Bad Request"},
                "404": {"description": "Not Found"},
                "503": {"description": "AI service unavailable"},
                "500": {"description": "Summarization failed"}
            }
        }
    },
    "/api/ai/translations": {
        "post": {
            "tags": ["AI - Translations"],
            "summary": "Create translation using AI",
            "description": "Translates a transcription using enhanced AI translation.",
            "security": [{"BearerAuth": []}],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "transcription_id": {"type": "integer"},
                                "target_language": {"type": "string"},
                                "high_quality": {"type": "boolean", "default": True}
                            },
                            "required": ["transcription_id", "target_language"]
                        }
                    }
                }
            },
            "responses": {
                "201": {
                    "description": "Translation created",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AI - Translation"}
                        }
                    }
                },
                "400": {"description": "Bad Request"},
                "404": {"description": "Not Found"},
                "500": {"description": "Translation failed"}
            }
        }
    },
    "/api/ai/medical-glossary/{source_lang}/{target_lang}": {
        "get": {
            "tags": ["AI - Translations"],
            "summary": "Fetch medical glossary by language pair",
            "description": "Returns a medical terminology glossary for the specified language pair.",
            "security": [{"BearerAuth": []}],
            "parameters": [
                {"name": "source_lang", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "target_lang", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {
                "200": {
                    "description": "Glossary retrieved",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "additionalProperties": {"type": "string"}}
                        }
                    }
                },
                "404": {"description": "Language pair not supported"},
                "500": {"description": "Glossary retrieval failed"}
            }
        }
    },
    "/api/ai/translations/{translation_id}/quality-check": {
        "get": {
            "tags": ["AI - Translations"],
            "summary": "Check translation quality using AI",
            "description": "Runs quality metrics on a translation using AI.",
            "security": [{"BearerAuth": []}],
            "parameters": [
                {"name": "translation_id", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            "responses": {
                "200": {
                    "description": "Quality check results",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "translation_id": {"type": "integer"},
                                    "quality_check": {
                                        "type": "object",
                                        "properties": {
                                            "fluency_score": {"type": "number"},
                                            "accuracy_score": {"type": "number"},
                                            "terminology_score": {"type": "number"},
                                            "overall_quality": {"type": "string"},
                                            "suggestions": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "400": {"description": "Bad Request"},
                "404": {"description": "Not Found"},
                "503": {"description": "AI service unavailable"},
                "500": {"description": "Quality check failed"}
            }
        }
    }
}


# Generate the OpenAPI specification
@swagger_bp.route('/openapi.json')
def openapi_spec():
    """
    Serve the OpenAPI specification as JSON
    """
    # Add all paths to spec
    for path, path_item in paths.items():
        spec.path(path=path, operations=path_item)

    return jsonify(spec.to_dict())


# Setup Swagger UI
swagger_ui_blueprint = get_swaggerui_blueprint(
    base_url='/api/docs',
    api_url='/api/openapi.json',
    config={
        'app_name': "Medical Transcription API",
        'layout': 'BaseLayout',
        'deepLinking': True,
        'displayOperationId': False,
        'defaultModelsExpandDepth': 3,
        'defaultModelExpandDepth': 3,
        'docExpansion': 'list',
        'showExtensions': True
    },
)


# Function to add Redoc UI
def setup_redoc(app):
    @app.route('/api/redoc')
    def redoc():
        return render_template('redoc.html')


def register_swagger(app):
    """
    Register Swagger and ReDoc with Flask application
    """
    # Register blueprint for OpenAPI specification
    app.register_blueprint(swagger_bp)

    # Register blueprint for Swagger UI
    app.register_blueprint(swagger_ui_blueprint, url_prefix='/api/docs')

    # Setup ReDoc
    setup_redoc(app)

    # Create template directory if it doesn't exist
    import os
    if not os.path.exists(os.path.join(app.root_path, 'templates')):
        os.makedirs(os.path.join(app.root_path, 'templates'))

        # Create ReDoc template
        redoc_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Medical Transcription API - ReDoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body {
                    margin: 0;
                    padding: 0;
                }
            </style>
        </head>
        <body>
            <redoc spec-url='/api/openapi.json' hide-hostname="true" expand-responses="200,201" path-in-middle-panel="true"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """

        # Write ReDoc template to file
        with open(os.path.join(app.root_path, 'templates', 'redoc.html'), 'w') as f:
            f.write(redoc_template)

        app.logger.info("Swagger and ReDoc documentation registered successfully")