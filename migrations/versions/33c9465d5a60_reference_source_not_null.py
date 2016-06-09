"""Reference.source NOT NULL

Revision ID: 33c9465d5a60
Revises: c92f30c03b62
Create Date: 2016-06-09 15:20:44.734913

"""

from __future__ import unicode_literals

# revision identifiers, used by Alembic.
revision = '33c9465d5a60'
down_revision = u'c92f30c03b62'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

def upgrade():
    # We repeat the data migration from migration c92f30c03b62, so we're sure
    # there are no NULL values left in the source column.
    connection = op.get_bind()

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

    # Unfortunately, SQLite doesn't support adding the NOT NULL constraint on
    # an existing column. We use batch_alter_table to workaround this.
    with op.batch_alter_table('references') as batch_op:
        batch_op.alter_column('source', nullable=False, existing_type=sa.Enum(
            'ncbi', 'ncbi_slice', 'lrg', 'url', 'upload', name='reference_source'))


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('references') as batch_op:
        batch_op.alter_column('source', nullable=True, existing_type=sa.Enum(
            'ncbi', 'ncbi_slice', 'lrg', 'url', 'upload', name='reference_source'))
    ### end Alembic commands ###
