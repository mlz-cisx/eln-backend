from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, \
    Text, event, BigInteger, UniqueConstraint, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from uuid import uuid4
from datetime import datetime

from joeseln_backend.ws.ws_client import transmit
from joeseln_backend.database.database import Base

from joeseln_backend.mylogging.root_logger import logger


class User(Base):
    __tablename__ = 'user'
    id = Column(BigInteger, primary_key=True)
    username = Column(Text, unique=True, index=True)
    email = Column(Text, unique=True)
    oidc_user = Column(Boolean, default=False)
    admin = Column(Boolean, default=False)
    deleted = Column(Boolean, default=False)
    password = Column(Text, default='not set')
    first_name = Column(Text)
    last_name = Column(Text)
    created_at = Column(DateTime)
    last_modified_at = Column(DateTime)


class Labbook(Base):
    __tablename__ = 'labbook'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    version_number = Column(Integer)
    deleted = Column(Boolean, default=False)
    title = Column(String, unique=True)
    strict_mode = Column(Boolean, default=False)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))
    description = Column(Text, default='')
    # __ts_vector__ = Column(TSVector(), Computed(
    #      "to_tsvector('english', title || ' ' || description)",
    #      persisted=True))
    # __table_args__ = (Index('ix_labbook___ts_vector__',
    #       __ts_vector__, postgresql_using='gin'),)


class Labbookchildelement(Base):
    __tablename__ = 'labbookchildelement'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    labbook_id = Column(UUID(as_uuid=True), ForeignKey(Labbook.id))
    deleted = Column(Boolean, default=False)
    position_x = Column(Integer)
    position_y = Column(Integer, index=True)
    width = Column(Integer)
    height = Column(Integer)
    child_object_id = Column(UUID(as_uuid=True))
    child_object_content_type = Column(Integer)
    child_object_content_type_model = Column(String)
    version_number = Column(Integer)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))


class Note(Base):
    __tablename__ = 'note'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    elem_id = Column(UUID(as_uuid=True), ForeignKey(Labbookchildelement.id))
    deleted = Column(Boolean, default=False)
    subject = Column(Text, default='')
    content = Column(Text, default='')
    version_number = Column(Integer)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))
    # __ts_vector__ = Column(TSVector(), Computed(
    #      "to_tsvector('english', subject || ' ' || content)",
    #      persisted=True))
    # __table_args__ = (Index('ix_note___ts_vector__',
    #       __ts_vector__, postgresql_using='gin'),)


class UploadEntry(Base):
    __tablename__ = 'upload_entry'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class FilePath(Base):
    __tablename__ = 'filepath'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class Picture(Base):
    __tablename__ = 'picture'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    elem_id = Column(UUID(as_uuid=True), ForeignKey(Labbookchildelement.id))
    # uploaded_picture_entry_id will convert to path
    uploaded_picture_entry_id = Column(UUID(as_uuid=True),
                                       ForeignKey(UploadEntry.id))
    deleted = Column(Boolean, default=False)
    title = Column(Text, default='')
    display = Column(Text, default='')
    width = Column(Integer)
    height = Column(Integer)
    version_number = Column(Integer)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))
    # png file path if it is background image for sketch,
    background_image = Column(Text, default='')
    # png file path if it is rendered image if you upload
    rendered_image = Column(Text, default='')
    # json file path for the shapes
    shapes_image = Column(Text, default='')
    # in bytes
    background_image_size = Column(BigInteger)
    rendered_image_size = Column(BigInteger)
    shapes_image_size = Column(BigInteger)
    scale = Column(Float, default=1)
    # __ts_vector__ = Column(TSVector(), Computed(
    #      "to_tsvector('english', title )",
    #      persisted=True))
    # __table_args__ = (Index('ix_picture___ts_vector__',
    #       __ts_vector__, postgresql_using='gin'),)


class File(Base):
    __tablename__ = 'file'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    elem_id = Column(UUID(as_uuid=True), ForeignKey(Labbookchildelement.id))
    uploaded_file_entry_id = Column(UUID(as_uuid=True),
                                    ForeignKey(UploadEntry.id))
    # path in projects storage
    path = Column(Text, default='')
    deleted = Column(Boolean, default=False)
    original_filename = Column(Text, default='')
    name = Column(Text, default='')
    display = Column(Text, default='')
    version_number = Column(Integer)
    # description title
    title = Column(Text, default='')
    imported = Column(Boolean, default=False)
    # editor content
    description = Column(Text, default='')
    plot_data = Column(Text, default='{}')
    mime_type = Column(Text, default='')
    file_size = Column(BigInteger)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))
    # __ts_vector__ = Column(TSVector(), Computed(
    #      "to_tsvector('english', title || ' ' || description)",
    #      persisted=True))
    # __table_args__ = (Index('ix_file___ts_vector__',
    #       __ts_vector__, postgresql_using='gin'),)


class Group(Base):
    __tablename__ = 'group'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # TODO consider group name as foreign key
    groupname = Column(String, unique=True)
    created_at = Column(DateTime)
    last_modified_at = Column(DateTime)


class Role(Base):
    __tablename__ = 'role'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    rolename = Column(Text, unique=True)
    description = Column(Text)
    created_at = Column(DateTime)
    last_modified_at = Column(DateTime)


class UserToGroupRole(Base):
    __tablename__ = 'user_to_group_role'
    __table_args__ = (UniqueConstraint('user_id', 'group_id', 'user_group_role',
                                       name='_user_to_group_role'),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(BigInteger, ForeignKey(User.id))
    group_id = Column(UUID(as_uuid=True), ForeignKey(Group.id))
    user_group_role = Column(UUID(as_uuid=True), ForeignKey(Role.id))
    created_at = Column(DateTime)
    last_modified_at = Column(DateTime)
    # user-group relation is configured by SSO or internal user management
    external = Column(Boolean)


class ChangesetChangeset(Base):
    __tablename__ = 'changeset_changeset'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    changeset_type = Column(Text)
    date = Column(DateTime)
    # Labbook id, Note_id
    object_uuid = Column(UUID(as_uuid=True), index=True)
    # Note content changed , Note title changed, ....
    object_type_id = Column(Integer)
    # for now with fake users
    user_id = Column(BigInteger, ForeignKey(User.id))
    # Not implemented
    object_id = Column(Integer)
    change_records = relationship("ChangesetChangerecord",
                                  backref="changeset_changeset")


class ChangesetChangerecord(Base):
    __tablename__ = 'changeset_changerecord'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # width, height, position_y, ....
    field_name = Column(Text)
    old_value = Column(Text)
    new_value = Column(Text)
    # not implemented
    is_related = Column(Boolean, default=False)
    change_set_id = Column(UUID(as_uuid=True),
                           ForeignKey(ChangesetChangeset.id))


class Version(Base):
    __tablename__ = 'version'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Labbook id, Note_id
    object_id = Column(UUID(as_uuid=True))
    # Metadata axample labbook
    # {"title": "Exp012", "metadata": [],
    #  "description": "<p>Hallo</p>",
    #  "child_elements":
    #    [
    #     {"width": 10, "height": 10, "position_x": 3, "position_y": 1,
    #      "lab_book_id": "29abfbd6-9bec-4f9b-a8da-26e8aca61f62",
    #      "child_object_id": "9d3c3c1a-60a1-4944-9d05-bcb476d7f4ea",
    #      "metadata_version": 1, "child_object_version_number": 3,
    #      "child_object_content_type_id": 42},
    #     {"width": 16, "height": 23, "position_x": 2, "position_y": 12,
    #      "lab_book_id": "29abfbd6-9bec-4f9b-a8da-26e8aca61f62",
    #      "child_object_id": "af1d0f15-bd67-496e-a5ff-4a0d68a97dc8",
    #      "metadata_version": 1, "child_object_version_number": 3,
    #      "child_object_content_type_id": 42}
    #      ],
    #      "metadata_version": 1}
    #
    # metadata example note
    # {
    #     "content": "<ol>\n<li>after versioning<br/><br/><br/><br/><br/><br/><br/></li>\n<li>lkajlAKJS</li>\n<li>LKJLK</li>\n</ol>",
    #     "subject": "Text", "metadata": [],
    #     "metadata_version": 1}
    version_metadata = Column(JSONB)
    # version Number , 3
    number = Column(Integer)
    # v3 of LabBook: Exp012
    summary = Column(Text)
    # display is summary
    display = Column(Text)
    # versioning for note could be 32
    content_type_pk = Column(Integer)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))
    # unique (content_type_id, object_id, number)


class Relation(Base):
    __tablename__ = 'relation'
    __table_args__ = (
        Index('comment_count', 'right_object_id', 'deleted', 'left_content_type'),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # comment id
    left_object_id = Column(UUID(as_uuid=True), index=True)
    # note id, ...
    right_object_id = Column(UUID(as_uuid=True), index=True)
    private = Column(Boolean, default=False)
    # comment
    left_content_type = Column(Integer)
    left_content_type_model = Column(Text)
    # note, file, image
    right_content_type = Column(Integer)
    right_content_type_model = Column(Text)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))
    version_number = Column(Integer)
    deleted = Column(Boolean, default=False)


class Comment(Base):
    __tablename__ = 'comment'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    deleted = Column(Boolean, default=False)
    content = Column(Text, default='')
    version_number = Column(Integer)
    created_at = Column(DateTime)
    created_by_id = Column(BigInteger, ForeignKey(User.id))
    last_modified_at = Column(DateTime)
    last_modified_by_id = Column(BigInteger, ForeignKey(User.id))


class UserConnectedWs(Base):
    __tablename__ = 'user_connected_ws'
    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, index=True)
    ws_id = Column(UUID(as_uuid=True), index=True)
    connected = Column(Boolean, default=False)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)


@event.listens_for(Note, "after_insert")
def note_insert_event(mapper, connection, target):
    logger.info(f'Note pk after insert: {target.id}')
    return


@event.listens_for(Note, "after_update")
def note_update_event(mapper, connection, target):
    try:
        transmit({'model_name': 'note', 'model_pk': str(target.id)})
    except RuntimeError as e:
        logger.error(e)
    logger.info(f'Note pk after update: {target.id}')
    return


@event.listens_for(Note, "after_delete")
def note_delete_event(mapper, connection, target):
    logger.info(f'Note pk after delete: {target.id}')
    return


#
@event.listens_for(Labbookchildelement, "after_insert")
def elem_insert_event(mapper, connection, target):
    logger.info(f'Element pk after insert : {target.id}')
    return


@event.listens_for(Labbookchildelement, "after_update")
def elem_update_event(mapper, connection, target):
    # logger.info(f'Element pk after update: {target.id}')
    return


@event.listens_for(Labbookchildelement, "after_delete")
def elem_delete_event(mapper, connection, target):
    logger.info(f'Element pk after delete: {target.id}')
    return
