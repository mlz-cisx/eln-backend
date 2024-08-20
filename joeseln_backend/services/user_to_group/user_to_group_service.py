from sqlalchemy import literal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from joeseln_backend.models import models
from joeseln_backend.services.role.role_service import get_role_by_rolename
from joeseln_backend.services.user.user_service import get_user_by_uname
from joeseln_backend.services.user_to_group.user_to_group_schema import *
from joeseln_backend.mylogging.root_logger import logger


def get_group_by_groupname(db: Session, groupname):
    return db.query(models.Group).filter_by(groupname=groupname).first()


def create_group(db: Session, groupname):
    db_group = models.Group(groupname=groupname,
                            created_at=datetime.datetime.now(),
                            last_modified_at=datetime.datetime.now()
                            )
    try:
        db.add(db_group)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    db.refresh(db_group)
    return db_group


def create_user_to_group(db: Session, user_to_group: UserToGroup_Create):
    db_group = models.UserToGroupRole(user_id=user_to_group.user_id,
                                      group_id=user_to_group.group_id,
                                      user_group_role=user_to_group.user_group_role,
                                      created_at=datetime.datetime.now(),
                                      last_modified_at=datetime.datetime.now()
                                      )
    try:
        db.add(db_group)
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    db.refresh(db_group)
    return db_group


def delete_user_to_group(db: Session, user_to_group: UserToGroup_Create):
    try:
        result = db.query(models.UserToGroupRole).filter(
            models.UserToGroupRole.user_group_role == user_to_group.user_group_role,
            models.UserToGroupRole.user_id == user_to_group.user_id,
            models.UserToGroupRole.group_id == user_to_group.group_id).delete()
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    logger.info(result)


def get_user_with_groups_by_uname(db: Session, username):
    user = db.query(models.User).filter_by(username=username).first()
    groups = get_user_groups(db=db, username=username)
    user.groups = groups
    return user


def get_user_group_roles(db: Session, username,
                         groupname):
    result = db.query(models.Role.rolename).join(models.UserToGroupRole,
                                                 models.Role.id == models.UserToGroupRole.user_group_role).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).join(
        models.Group,
        models.Group.id == models.UserToGroupRole.group_id).filter(
        models.User.username == username).filter(
        models.Group.groupname == groupname).all()
    return result


def get_user_group_roles_with_match(db: Session, username,
                                    groupname):
    result = db.query(models.Role.rolename).join(models.UserToGroupRole,
                                                 models.Role.id == models.UserToGroupRole.user_group_role).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).join(
        models.Group,
        models.Group.id == models.UserToGroupRole.group_id).filter(
        models.User.username == username).filter(
        literal(groupname).contains(models.Group.groupname)).all()
    return result


def get_user_groups(db: Session, username):
    result = db.query(models.Group).join(models.UserToGroupRole,
                                         models.Group.id == models.UserToGroupRole.group_id).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).filter(
        models.User.username == username).all()

    result = [x.groupname for x in result]

    return result


def get_user_groups_role_user(db: Session, username):
    result = db.query(models.Group).join(models.UserToGroupRole,
                                         models.Group.id == models.UserToGroupRole.group_id).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).join(
        models.Role,
        models.Role.id == models.UserToGroupRole.user_group_role).filter(
        models.User.username == username, models.Role.rolename == 'user').all()
    result = [x.groupname for x in result]
    return result


def get_user_groups_role_groupadmin(db: Session, username):
    result = db.query(models.Group).join(models.UserToGroupRole,
                                         models.Group.id == models.UserToGroupRole.group_id).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).join(
        models.Role,
        models.Role.id == models.UserToGroupRole.user_group_role).filter(
        models.User.username == username,
        models.Role.rolename == 'groupadmin').all()
    result = [x.groupname for x in result]
    return result


def update_oidc_user_groups(db: Session, user):
    oidc_groups = user.groups
    logger.info(oidc_groups)
    user_groups = get_user_groups_role_user(db=db, username=user.username)
    logger.info(user_groups)

    for oidc_group in oidc_groups:
        if not get_group_by_groupname(db=db, groupname=oidc_group):
            create_group(db=db, groupname=oidc_group)
        if oidc_group not in user_groups:
            add_as_user_to_group(db=db, username=user.username,
                                 groupname=oidc_group)

    for user_group in user_groups:
        if user_group not in oidc_groups:
            remove_as_user_from_group(db=db, username=user.username,
                                      groupname=user_group)

    user_groups = get_user_groups_role_user(db=db, username=user.username)
    logger.info(user_groups)


def check_for_admin_role(db: Session, username):
    result = db.query(models.Role).join(models.UserToGroupRole,
                                        models.Role.id == models.UserToGroupRole.user_group_role).join(
        models.User, models.UserToGroupRole.user_id == models.User.id).join(
        models.Group,
        models.Group.id == models.UserToGroupRole.group_id).filter(
        models.User.username == username).filter(
        models.Role.rolename == 'admin').all()
    return bool(int(len(result)))


def remove_all_admin_roles(db: Session, username):
    try:
        role = db.query(models.Role).filter(
            models.Role.rolename == 'admin').first()
        user = db.query(models.User).filter(
            models.User.username == username).first()
        result = db.query(models.UserToGroupRole).filter(
            models.UserToGroupRole.user_group_role == role.id,
            models.UserToGroupRole.user_id == user.id).delete()
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    logger.info(result)


def remove_all_group_roles(db: Session, username, groupname):
    try:
        groups = db.query(models.Group).filter(
            models.Group.groupname == groupname).all()
        user = db.query(models.User).filter(
            models.User.username == username).first()
        result = db.query(models.UserToGroupRole).filter(
            models.UserToGroupRole.group_id.in_([group.id for group in groups]),
            models.UserToGroupRole.user_id == user.id).delete()
        db.commit()
    except SQLAlchemyError as e:
        logger.error(e)
        return
    logger.info(result)


def add_as_user_to_group(db: Session, username, groupname):
    user_role_group = {
        'user_id': get_user_by_uname(db=db, username=username).id,
        'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
        'user_group_role': get_role_by_rolename(db=db, rolename='user').id
    }
    db_user_to_group = create_user_to_group(db=db,
                                            user_to_group=UserToGroup_Create.parse_obj(
                                                user_role_group))

    logger.info(db_user_to_group)


def remove_as_user_from_group(db: Session, username, groupname):
    user_role_group = {
        'user_id': get_user_by_uname(db=db, username=username).id,
        'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
        'user_group_role': get_role_by_rolename(db=db, rolename='user').id
    }
    delete_user_to_group(db=db, user_to_group=UserToGroup_Create.parse_obj(
        user_role_group))


def add_as_groupadmin_to_group(db: Session, username, groupname):
    user_role_group = {
        'user_id': get_user_by_uname(db=db, username=username).id,
        'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
        'user_group_role': get_role_by_rolename(db=db, rolename='groupadmin').id
    }
    db_user_to_group = create_user_to_group(db=db,
                                            user_to_group=UserToGroup_Create.parse_obj(
                                                user_role_group))

    logger.info(db_user_to_group)


def remove_as_groupadmin_from_group(db: Session, username, groupname):
    user_role_group = {
        'user_id': get_user_by_uname(db=db, username=username).id,
        'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
        'user_group_role': get_role_by_rolename(db=db, rolename='groupadmin').id
    }
    delete_user_to_group(db=db, user_to_group=UserToGroup_Create.parse_obj(
        user_role_group))


def add_as_admin_to_group(db: Session, username, groupname):
    user_role_group = {
        'user_id': get_user_by_uname(db=db, username=username).id,
        'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
        'user_group_role': get_role_by_rolename(db=db, rolename='admin').id
    }
    db_user_to_group = create_user_to_group(db=db,
                                            user_to_group=UserToGroup_Create.parse_obj(
                                                user_role_group))

    logger.info(db_user_to_group)
