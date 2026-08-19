"""Base migration - Vision Ecosystem v0.1 tables

Revision ID: 1045e5167ab8
Revises: 
Create Date: 2026-08-18T06:41:26.904582

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '1045e5167ab8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # tenants
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('settings', postgresql.JSONB, default=dict),
        sa.Column('branding', postgresql.JSONB, default=dict),
        sa.Column('plan', sa.String(50), default='basic'),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('clerk_id', sa.String(255), unique=True),
        sa.Column('email', sa.String(255)),
        sa.Column('full_name', sa.String(255)),
        sa.Column('role', sa.String(50), default='talent'),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # profiles
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('full_name', sa.String(255)),
        sa.Column('birth_date', sa.Date),
        sa.Column('gender', sa.String(50)),
        sa.Column('height_cm', sa.Integer),
        sa.Column('weight_kg', sa.Numeric(5, 2)),
        sa.Column('eye_color', sa.String(50)),
        sa.Column('hair_color', sa.String(50)),
        sa.Column('skin_tone', sa.String(50)),
        sa.Column('body_type', sa.String(50)),
        sa.Column('shoe_size', sa.String(20)),
        sa.Column('dress_size', sa.String(20)),
        sa.Column('pants_size', sa.String(20)),
        sa.Column('shirt_size', sa.String(20)),
        sa.Column('special_skills', postgresql.ARRAY(sa.String)),
        sa.Column('languages', postgresql.ARRAY(sa.String)),
        sa.Column('experience_level', sa.String(50)),
        sa.Column('availability', sa.String(100)),
        sa.Column('location', sa.String(255)),
        sa.Column('bio', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # photoshoots
    op.create_table(
        'photoshoots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('photographer', sa.String(255)),
        sa.Column('location', sa.String(255)),
        sa.Column('shoot_date', sa.Date),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # photos
    op.create_table(
        'photos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('photoshoot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('photoshoots.id')),
        sa.Column('file_url', sa.Text, nullable=False),
        sa.Column('thumbnail_url', sa.Text),
        sa.Column('angle', sa.String(50)),
        sa.Column('format', sa.String(50)),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # analyses
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('photo_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('photos.id')),
        sa.Column('facial_analysis', postgresql.JSONB),
        sa.Column('visagism_analysis', postgresql.JSONB),
        sa.Column('expression_analysis', postgresql.JSONB),
        sa.Column('photogenic_analysis', postgresql.JSONB),
        sa.Column('colorimetry_analysis', postgresql.JSONB),
        sa.Column('grooming_analysis', postgresql.JSONB),
        sa.Column('casting_analysis', postgresql.JSONB),
        sa.Column('branding_analysis', postgresql.JSONB),
        sa.Column('overall_score', sa.Numeric(4, 2)),
        sa.Column('recommendations', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # reports
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('type', sa.String(50)),
        sa.Column('content', postgresql.JSONB),
        sa.Column('pdf_url', sa.Text),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('previous_version_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # evaluations
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.id')),
        sa.Column('evaluator', sa.String(255)),
        sa.Column('scores', postgresql.JSONB),
        sa.Column('comments', sa.Text),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # digital_twin_assets
    op.create_table(
        'digital_twin_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('media_type', sa.String(50), nullable=False),
        sa.Column('file_url', sa.Text, nullable=False),
        sa.Column('angle', sa.String(50)),
        sa.Column('pose', sa.String(50)),
        sa.Column('expression', sa.String(50)),
        sa.Column('tags', postgresql.ARRAY(sa.String)),
        sa.Column('quality_score', sa.Numeric(3, 2)),
        sa.Column('embedding', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # castings
    op.create_table(
        'castings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('requirements', postgresql.JSONB),
        sa.Column('deadline', sa.Date),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # casting_matches
    op.create_table(
        'casting_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('casting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('castings.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('compatibility_score', sa.Numeric(5, 2)),
        sa.Column('matching_attributes', postgresql.JSONB),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # content_items
    op.create_table(
        'content_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('content_type', sa.String(50)),
        sa.Column('content_data', postgresql.JSONB),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # content_approvals
    op.create_table(
        'content_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('content_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content_items.id'), nullable=False),
        sa.Column('approval_type', sa.String(50)),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('revision_notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ai_tasks
    op.create_table(
        'ai_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('task_type', sa.String(100)),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('result', postgresql.JSONB),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(100)),
        sa.Column('entity_type', sa.String(100)),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True)),
        sa.Column('before_state', postgresql.JSONB),
        sa.Column('after_state', postgresql.JSONB),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('user_agent', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )

    # voice_commands
    op.create_table(
        'voice_commands',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('audio_url', sa.Text),
        sa.Column('transcription', sa.Text),
        sa.Column('recognized_intent', sa.String(100)),
        sa.Column('confidence', sa.Numeric(3, 2)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )

    # workflows
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('steps', postgresql.JSONB),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # workflow_runs
    op.create_table(
        'workflow_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id'), nullable=False),
        sa.Column('status', sa.String(50), default='running'),
        sa.Column('step_results', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # notifications
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('type', sa.String(50)),
        sa.Column('channel', sa.String(50)),
        sa.Column('title', sa.String(255)),
        sa.Column('message', sa.Text),
        sa.Column('data', postgresql.JSONB),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
    )

    # Career Memory tables (v0.1)
    op.create_table(
        'professional_experiences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('title', sa.String(255)),
        sa.Column('company', sa.String(255)),
        sa.Column('project_name', sa.String(255)),
        sa.Column('role', sa.String(100)),
        sa.Column('character_name', sa.String(100)),
        sa.Column('production_type', sa.String(100)),
        sa.Column('director', sa.String(255)),
        sa.Column('agency', sa.String(255)),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('location', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('skills_used', postgresql.ARRAY(sa.String)),
        sa.Column('photos_used', postgresql.ARRAY(sa.Text)),
        sa.Column('video_url', sa.Text),
        sa.Column('is_featured', sa.Boolean, default=False),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'characters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('archetype', sa.String(100)),
        sa.Column('is_simulated', sa.Boolean, default=False),
        sa.Column('simulation_prompt', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('brand', sa.String(255)),
        sa.Column('campaign_type', sa.String(100)),
        sa.Column('deliverables', postgresql.ARRAY(sa.String)),
        sa.Column('results', postgresql.JSONB),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'agencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('specialties', postgresql.ARRAY(sa.String)),
        sa.Column('location', sa.String(255)),
        sa.Column('website', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'agency_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('agency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agencies.id'), nullable=False),
        sa.Column('contact_name', sa.String(255)),
        sa.Column('contact_email', sa.String(255)),
        sa.Column('contact_phone', sa.String(50)),
        sa.Column('contract_type', sa.String(50)),
        sa.Column('commission_rate', sa.Numeric(5, 2)),
        sa.Column('start_date', sa.Date),
        sa.Column('end_date', sa.Date),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'career_feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('source', sa.String(100)),
        sa.Column('source_name', sa.String(255)),
        sa.Column('feedback_type', sa.String(100)),
        sa.Column('feedback_text', sa.Text),
        sa.Column('rating', sa.Numeric(3, 2)),
        sa.Column('related_experience_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('professional_experiences.id')),
        sa.Column('related_casting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('castings.id')),
        sa.Column('is_positive', sa.Boolean),
        sa.Column('action_taken', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'appearance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('record_type', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('style_elements', postgresql.JSONB),
        sa.Column('photos', postgresql.ARRAY(sa.Text)),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'style_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('category', sa.String(100)),
        sa.Column('preference', sa.String(255)),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('success_rate', sa.Numeric(5, 2)),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'content_performances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('content_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('content_items.id')),
        sa.Column('platform', sa.String(50)),
        sa.Column('metrics', postgresql.JSONB),
        sa.Column('engagement_rate', sa.Numeric(5, 4)),
        sa.Column('best_performing', sa.String(50)),
        sa.Column('audience_demographics', postgresql.JSONB),
        sa.Column('peak_hours', postgresql.ARRAY(sa.String)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    # Drop in reverse order
    op.drop_table('content_performances')
    op.drop_table('style_preferences')
    op.drop_table('appearance_records')
    op.drop_table('career_feedbacks')
    op.drop_table('agency_contacts')
    op.drop_table('agencies')
    op.drop_table('campaigns')
    op.drop_table('characters')
    op.drop_table('professional_experiences')
    op.drop_table('notifications')
    op.drop_table('workflow_runs')
    op.drop_table('workflows')
    op.drop_table('voice_commands')
    op.drop_table('audit_logs')
    op.drop_table('ai_tasks')
    op.drop_table('content_approvals')
    op.drop_table('content_items')
    op.drop_table('casting_matches')
    op.drop_table('castings')
    op.drop_table('digital_twin_assets')
    op.drop_table('evaluations')
    op.drop_table('reports')
    op.drop_table('analyses')
    op.drop_table('photos')
    op.drop_table('photoshoots')
    op.drop_table('profiles')
    op.drop_table('users')
    op.drop_table('tenants')
