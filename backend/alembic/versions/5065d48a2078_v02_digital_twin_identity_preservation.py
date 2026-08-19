"""Vision Ecosystem v0.2 - Digital Twin Versioning, Identity/Appearance/Character separation, Identity Preservation

Revision ID: 5065d48a2078
Revises: 1045e5167ab8
Create Date: 2026-08-18T06:41:26.904582

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '5065d48a2078'
down_revision = '1045e5167ab8'
branch_labels = None
depends_on = None


def upgrade():
    # ========== ETAPA 2: DIGITAL TWIN VERSIONING ==========
    op.create_table(
        'digital_twin_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False, default=1),
        sa.Column('version_name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('created_reason', sa.String(100)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('assets_summary', postgresql.JSONB, default=dict),
        sa.Column('identity_traits_snapshot', postgresql.JSONB, default=dict),
        sa.Column('appearance_state_snapshot', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ========== ETAPA 3: IDENTITY / APPEARANCE / CHARACTER ==========
    op.create_table(
        'identity_traits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('trait_category', sa.String(100), nullable=False),
        sa.Column('trait_name', sa.String(100), nullable=False),
        sa.Column('trait_value', sa.Text, nullable=False),
        sa.Column('confidence', sa.Numeric(3, 2), default=1.0),
        sa.Column('source', sa.String(100), default='analysis'),
        sa.Column('verified_by', sa.String(255)),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('is_permanent', sa.String(50), default='true'),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('_metadata', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'appearance_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('digital_twin_versions.id')),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('attribute', sa.String(100), nullable=False),
        sa.Column('current_value', sa.Text, nullable=False),
        sa.Column('previous_value', sa.Text),
        sa.Column('changed_at', sa.DateTime(timezone=True)),
        sa.Column('changed_reason', sa.String(255)),
        sa.Column('photos', postgresql.ARRAY(sa.Text)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('_metadata', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'character_transformations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('character_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('characters.id')),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('digital_twin_versions.id')),
        sa.Column('transformation_type', sa.String(100), nullable=False),
        sa.Column('attribute', sa.String(100), nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('is_simulated', sa.String(50), default='true'),
        sa.Column('simulation_prompt_fragment', sa.Text),
        sa.Column('generated_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('digital_twin_assets.id')),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('_metadata', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ========== ETAPA 5: IDENTITY PRESERVATION ==========
    op.create_table(
        'identity_references',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('digital_twin_assets.id')),
        sa.Column('reference_type', sa.String(100), nullable=False),
        sa.Column('origin', sa.String(100), nullable=False),
        sa.Column('file_url', sa.Text, nullable=False),
        sa.Column('quality_score', sa.Numeric(3, 2)),
        sa.Column('embedding', postgresql.JSONB),
        sa.Column('landmarks', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, default=dict),
        sa.Column('is_primary', sa.String(50), default='false'),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        'asset_origin_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('digital_twin_assets.id')),
        sa.Column('asset_type', sa.String(100), nullable=False),
        sa.Column('origin', sa.String(100), nullable=False),
        sa.Column('source_description', sa.Text),
        sa.Column('generated_by', sa.String(100)),
        sa.Column('generation_prompt', sa.Text),
        sa.Column('parent_asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('digital_twin_assets.id')),
        sa.Column('is_saved_as_real', sa.String(50), default='false'),
        sa.Column('warning_flags', postgresql.ARRAY(sa.String), default=list),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Criar indices para performance
    op.create_index('idx_digital_twin_versions_profile', 'digital_twin_versions', ['profile_id'])
    op.create_index('idx_identity_traits_profile', 'identity_traits', ['profile_id'])
    op.create_index('idx_appearance_states_profile', 'appearance_states', ['profile_id'])
    op.create_index('idx_character_transformations_profile', 'character_transformations', ['profile_id'])
    op.create_index('idx_identity_references_profile', 'identity_references', ['profile_id'])
    op.create_index('idx_asset_origin_logs_profile', 'asset_origin_logs', ['profile_id'])
    op.create_index('idx_identity_references_origin', 'identity_references', ['origin'])


def downgrade():
    op.drop_index('idx_identity_references_origin')
    op.drop_index('idx_asset_origin_logs_profile')
    op.drop_index('idx_identity_references_profile')
    op.drop_index('idx_character_transformations_profile')
    op.drop_index('idx_appearance_states_profile')
    op.drop_index('idx_identity_traits_profile')
    op.drop_index('idx_digital_twin_versions_profile')

    op.drop_table('asset_origin_logs')
    op.drop_table('identity_references')
    op.drop_table('character_transformations')
    op.drop_table('appearance_states')
    op.drop_table('identity_traits')
    op.drop_table('digital_twin_versions')
