"""Add Reference.source

Revision ID: c92f30c03b62
Revises: 56ddeb75114e
Create Date: 2016-06-02 18:12:08.511811

"""

from __future__ import unicode_literals

# revision identifiers, used by Alembic.
revision = 'c92f30c03b62'
down_revision = u'56ddeb75114e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql


def upgrade():
    # We want to add a NOT NULL column without default value. So we first add
    # the column without the constraint, then populate it, then add the
    # constraint.
    # Since a live deployment might be adding entries with a NULL value for
    # the new column, even *during* this migration, we postpone adding the
    # constraint to a later release where we are sure that no old version of
    # the codebase is running that might do such a thing.

    connection = op.get_bind()

    # https://bitbucket.org/zzzeek/alembic/issue/89/opadd_column-and-opdrop_column-should
    context = op.get_context()
    if context.bind.dialect.name == 'postgresql':
        has_reference_source_type = context.bind.execute(
            "select exists (select 1 from pg_type "
            "where typname='reference_source')").scalar()
        if not has_reference_source_type:
            op.execute("CREATE TYPE reference_source AS ENUM ('ncbi', 'ncbi_slice', 'lrg', 'url', 'upload')")

    # Columns `source` and `source_data` will make `geninfo_identifier`,
    # `slice_*`, and `download_url` obsolete.
    op.add_column('references', sa.Column(
        'source', sa.Enum('ncbi', 'ncbi_slice', 'lrg', 'url', 'upload', name='reference_source'),
        nullable=True))
    op.add_column('references', sa.Column(
        'source_data', sa.String(length=255), nullable=True))

    # Inline table definition we can use in this migration.
    references = sql.table(
        'references',
        sql.column('id', sa.Integer()),
        sql.column('accession', sa.String(20)),
        sql.column('source', sa.Enum('ncbi', 'ncbi_slice', 'lrg', 'url', 'upload', name='reference_source')),
        sql.column('source_data', sa.String(255)),
        sql.column('geninfo_identifier', sa.String(13)),
        sql.column('slice_accession', sa.String(20)),
        sql.column('slice_start', sa.Integer()),
        sql.column('slice_stop', sa.Integer()),
        sql.column('slice_orientation', sa.Enum('forward', 'reverse', name='slice_orientation')),
        sql.column('download_url', sa.String(255)))

    # Get all rows.
    result = connection.execute(
        references.select().with_only_columns([
            references.c.id,
            references.c.accession,
            references.c.source,
            references.c.source_data,
            references.c.geninfo_identifier,
            references.c.slice_accession,
            references.c.slice_start,
            references.c.slice_stop,
            references.c.slice_orientation,
            references.c.download_url]))

    # Generate parameter values for the UPDATE query below.
    def update_params(r):
        data = None
        if r.source:
            source = r.source
            data = r.source_data
        if r.accession.startswith('LRG_'):
            source = 'lrg'
        elif r.slice_accession:
            source = 'ncbi_slice'
            data = '{}:{}:{}:{}'.format(r.slice_accession, r.slice_start, r.slice_stop, r.slice_orientation)
        elif r.download_url:
            source = 'url'
            data = r.download_url
        elif r.geninfo_identifier:
            source = 'ncbi'
        else:
            source = 'upload'
        return {'r_id': r.id, 'r_source': source, 'r_source_data': data}

    # Process a few rows at a time, since they will be read in memory.
    while True:
        chunk = result.fetchmany(1000)
        if not chunk:
            break

        # Populate `source` and `source_data` based on existing column values.
        statement = references.update().where(
            references.c.id == sql.bindparam('r_id')
        ).values({'source': sql.bindparam('r_source'),
                  'source_data': sql.bindparam('r_source_data')})

        # Execute UPDATE query for fetched rows.
        connection.execute(statement, [update_params(r) for r in chunk])

    op.create_index('reference_source_data', 'references', ['source', 'source_data'], unique=False)


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('reference_source_data', table_name='references')
    op.drop_column('references', 'source_data')
    op.drop_column('references', 'source')

    # https://bitbucket.org/zzzeek/alembic/issue/89/opadd_column-and-opdrop_column-should
    context = op.get_context()
    if context.bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS reference_source')
    ### end Alembic commands ###
