from sqlalchemy import literal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from sqlalchemy import or_

from joeseln_backend.helper import db_ordering
from joeseln_backend.models import models
from joeseln_backend.services.role.role_service import get_role_by_rolename
from joeseln_backend.services.user.user_service import get_user_by_uname
from joeseln_backend.services.user_to_group.user_to_group_schema import *
from joeseln_backend.mylogging.root_logger import logger


def get_all_groups(db: Session, params, user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if user.admin:
        if params.get('search'):
            search_text = params.get('search')
            groups = db.query(models.Group).filter(
                models.Group.groupname.ilike(f'%{search_text}%')).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()
        else:
            groups = db.query(models.Group).order_by(
                text(order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

        return groups
    return


def get_all_groupusers(db: Session, group_pk, params, authed_user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if 'id' in order_params:
        modified_order_params = 'user_to_group_role.user_id asc'
    else:
        modified_order_params = order_params

    group_user = not bool(params.get('deleted'))

    if authed_user.admin:
        if params.get('search'):
            search_text = params.get('search')
            users = db.query(models.User).join(models.UserToGroupRole,
                                               models.User.id == models.UserToGroupRole.user_id) \
                .join(
                models.Role,
                models.Role.id == models.UserToGroupRole.user_group_role).filter(
                models.UserToGroupRole.group_id == group_pk,
                models.Role.rolename == 'user').filter(or_(
                models.User.username.ilike(f'%{search_text}%'),
                models.User.first_name.ilike(f'%{search_text}%'),
                models.User.last_name.ilike(f'%{search_text}%'),
            )).order_by(
                text(modified_order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

            if not group_user:

                all_other_users = db.query(models.User).filter_by(
                    admin=False).filter(or_(
                    models.User.username.ilike(f'%{search_text}%'),
                    models.User.first_name.ilike(f'%{search_text}%'),
                    models.User.last_name.ilike(f'%{search_text}%'),
                )).order_by(
                    text(order_params)).offset(params.get('offset')).limit(
                    params.get('limit')).all()

                for user_elem in users:
                    if user_elem in all_other_users:
                        all_other_users.remove(user_elem)

                for user_elem in all_other_users:
                    user_elem.in_group = False
                return all_other_users

            for user_elem in users:
                user_elem.in_group = True
            return users


        else:
            users = db.query(models.User).join(models.UserToGroupRole,
                                               models.User.id == models.UserToGroupRole.user_id) \
                .join(
                models.Role,
                models.Role.id == models.UserToGroupRole.user_group_role).filter(
                models.UserToGroupRole.group_id == group_pk,
                models.Role.rolename == 'user') \
                .order_by(
                text(modified_order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

            if not group_user:
                all_other_users = db.query(models.User).filter_by(
                    admin=False).order_by(
                    text(order_params)).offset(params.get('offset')).limit(
                    params.get('limit')).all()
                for user_elem in users:
                    if user_elem in all_other_users:
                        all_other_users.remove(user_elem)

                for user_elem in all_other_users:
                    user_elem.in_group = False
                return all_other_users

            for user_elem in users:
                user_elem.in_group = True
            return users
    return


def get_all_groupadmins(db: Session, group_pk, params, authed_user):
    order_params = db_ordering.get_order_params(ordering=params.get('ordering'))

    if 'id' in order_params:
        modified_order_params = 'user_to_group_role.user_id asc'
    else:
        modified_order_params = order_params

    group_groupadmin = not bool(params.get('deleted'))

    if authed_user.admin:
        if params.get('search'):
            search_text = params.get('search')
            users = db.query(models.User).join(models.UserToGroupRole,
                                               models.User.id == models.UserToGroupRole.user_id) \
                .join(
                models.Role,
                models.Role.id == models.UserToGroupRole.user_group_role).filter(
                models.UserToGroupRole.group_id == group_pk,
                models.Role.rolename == 'groupadmin').filter(or_(
                models.User.username.ilike(f'%{search_text}%'),
                models.User.first_name.ilike(f'%{search_text}%'),
                models.User.last_name.ilike(f'%{search_text}%'),
            )).order_by(
                text(modified_order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

            if not group_groupadmin:

                all_other_users = db.query(models.User).filter_by(
                    admin=False).filter(or_(
                    models.User.username.ilike(f'%{search_text}%'),
                    models.User.first_name.ilike(f'%{search_text}%'),
                    models.User.last_name.ilike(f'%{search_text}%'),
                )).order_by(
                    text(order_params)).offset(params.get('offset')).limit(
                    params.get('limit')).all()

                for user_elem in users:
                    if user_elem in all_other_users:
                        all_other_users.remove(user_elem)

                for user_elem in all_other_users:
                    user_elem.in_group = False
                return all_other_users

            for user_elem in users:
                user_elem.in_group = True
            return users


        else:
            users = db.query(models.User).join(models.UserToGroupRole,
                                               models.User.id == models.UserToGroupRole.user_id) \
                .join(
                models.Role,
                models.Role.id == models.UserToGroupRole.user_group_role).filter(
                models.UserToGroupRole.group_id == group_pk,
                models.Role.rolename == 'groupadmin') \
                .order_by(
                text(modified_order_params)).offset(params.get('offset')).limit(
                params.get('limit')).all()

            if not group_groupadmin:
                all_other_users = db.query(models.User).filter_by(
                    admin=False).order_by(
                    text(order_params)).offset(params.get('offset')).limit(
                    params.get('limit')).all()
                for user_elem in users:
                    if user_elem in all_other_users:
                        all_other_users.remove(user_elem)
                for user_elem in all_other_users:
                    user_elem.in_group = False
                return all_other_users

            for user_elem in users:
                user_elem.in_group = True
            return users
    return


def get_group_by_groupname(db: Session, groupname):
    return db.query(models.Group).filter_by(groupname=groupname).first()


def get_groupname(db: Session, group_pk, user):
    if user.admin:
        group = db.query(models.Group).get(group_pk)
        return group.groupname
    return


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
        db.close()
        return
    db.refresh(db_group)
    db.close()
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
        db.close()
        return
    db.refresh(db_group)
    db.close()
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
        db.close()
        return
    logger.info(result)
    db.close()
    return result


def get_user_with_groups_by_uname(db: Session, username):
    user = db.query(models.User).filter_by(username=username).first()
    groups = get_user_groups(db=db, username=username)
    admin_groups = get_user_groups_role_groupadmin(db=db,
                                                   username=username)
    user.groups = groups
    user.admin_groups = admin_groups
    try:
        del user.password
        # del user.admin
        del user.created_at
        del user.last_modified_at
        # del user.oidc_user
    except KeyError as e:
        print(e)

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


def get_groupuser(db: Session, username):
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
    user_groups = get_user_groups_role_user(db=db, username=user.username)

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

    # user_groups = get_user_groups_role_user(db=db, username=user.username)
    # logger.info(user_groups)


def check_for_admin_role(db: Session, username):
    user = db.query(models.User).filter(
        models.User.username == username).first()
    return user.admin


def check_for_admin_role_with_user_id(db: Session, user_id):
    user = db.query(models.User).get(user_id)
    return user.admin


def add_admin_role(db: Session, username):
    success = False
    user = db.query(models.User).filter(
        models.User.username == username).first()
    if user:
        user.admin = True
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return success
        db.refresh(user)
        db.close()
        success = True
        return success
    return success


def remove_admin_role(db: Session, username):
    success = False
    user = db.query(models.User).filter(
        models.User.username == username).first()
    if user:
        user.admin = False
        try:
            db.commit()
        except SQLAlchemyError as e:
            logger.error(e)
            db.close()
            return success
        db.refresh(user)
        db.close()
        success = True
        return success
    return success


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
        db.close()
        return
    db.close()
    logger.info(result)


def add_as_user_to_group(db: Session, username, groupname):
    user = get_user_by_uname(db=db, username=username)
    group = get_group_by_groupname(db=db, groupname=groupname)
    role = get_role_by_rolename(db=db, rolename='user')

    if user is not None and group is not None and role is not None:
        user_role_group = {
            'user_id': get_user_by_uname(db=db, username=username).id,
            'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
            'user_group_role': get_role_by_rolename(db=db, rolename='user').id
        }
        db_user_to_group = create_user_to_group(db=db,
                                                user_to_group=UserToGroup_Create.parse_obj(
                                                    user_role_group))

        logger.info(db_user_to_group)
        return db_user_to_group

    return


def gui_add_as_user_to_group(db: Session, authed_user, user_id, group_pk):
    if authed_user.admin:
        user = db.query(models.User).get(user_id)
        group = db.query(models.Group).get(group_pk)
        role = get_role_by_rolename(db=db, rolename='user')

        if user is not None and group is not None and role is not None:
            user_role_group = {
                'user_id': user_id,
                'group_id': group_pk,
                'user_group_role': get_role_by_rolename(db=db,
                                                        rolename='user').id
            }
            db_user_to_group = create_user_to_group(db=db,
                                                    user_to_group=UserToGroup_Create.parse_obj(
                                                        user_role_group))

            return db_user_to_group
        return
    return


def remove_as_user_from_group(db: Session, username, groupname):
    user = get_user_by_uname(db=db, username=username)
    group = get_group_by_groupname(db=db, groupname=groupname)
    role = get_role_by_rolename(db=db, rolename='user')

    if user is not None and group is not None and role is not None:
        user_role_group = {
            'user_id': get_user_by_uname(db=db, username=username).id,
            'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
            'user_group_role': get_role_by_rolename(db=db, rolename='user').id
        }
        return delete_user_to_group(db=db,
                                    user_to_group=UserToGroup_Create.parse_obj(
                                        user_role_group))
    return


def gui_remove_as_user_from_group(db: Session, authed_user, user_id, group_pk):
    if authed_user.admin:
        user = db.query(models.User).get(user_id)
        group = db.query(models.Group).get(group_pk)
        role = get_role_by_rolename(db=db, rolename='user')

        if user is not None and group is not None and role is not None:
            user_role_group = {
                'user_id': user_id,
                'group_id': group_pk,
                'user_group_role': get_role_by_rolename(db=db,
                                                        rolename='user').id
            }
            return delete_user_to_group(db=db,
                                        user_to_group=UserToGroup_Create.parse_obj(
                                            user_role_group))
        return
    return


def add_as_groupadmin_to_group(db: Session, username, groupname):
    user = get_user_by_uname(db=db, username=username)
    group = get_group_by_groupname(db=db, groupname=groupname)
    role = get_role_by_rolename(db=db, rolename='groupadmin')

    if user is not None and group is not None and role is not None:
        user_role_group = {
            'user_id': get_user_by_uname(db=db, username=username).id,
            'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
            'user_group_role': get_role_by_rolename(db=db,
                                                    rolename='groupadmin').id
        }
        db_user_to_group = create_user_to_group(db=db,
                                                user_to_group=UserToGroup_Create.parse_obj(
                                                    user_role_group))

        logger.info(db_user_to_group)
        return db_user_to_group

    return False


def gui_add_as_groupadmin_to_group(db: Session, authed_user, user_id, group_pk):
    if authed_user.admin:
        user = db.query(models.User).get(user_id)
        group = db.query(models.Group).get(group_pk)
        role = get_role_by_rolename(db=db, rolename='groupadmin')

        if user is not None and group is not None and role is not None:
            user_role_group = {
                'user_id': user_id,
                'group_id': group_pk,
                'user_group_role': get_role_by_rolename(db=db,
                                                        rolename='groupadmin').id
            }
            db_user_to_group = create_user_to_group(db=db,
                                                    user_to_group=UserToGroup_Create.parse_obj(
                                                        user_role_group))

            return db_user_to_group
        return
    return


def remove_as_groupadmin_from_group(db: Session, username, groupname):
    user = get_user_by_uname(db=db, username=username)
    group = get_group_by_groupname(db=db, groupname=groupname)
    role = get_role_by_rolename(db=db, rolename='groupadmin')

    if user is not None and group is not None and role is not None:
        user_role_group = {
            'user_id': get_user_by_uname(db=db, username=username).id,
            'group_id': get_group_by_groupname(db=db, groupname=groupname).id,
            'user_group_role': get_role_by_rolename(db=db,
                                                    rolename='groupadmin').id
        }
        return delete_user_to_group(db=db,
                                    user_to_group=UserToGroup_Create.parse_obj(
                                        user_role_group))

    return


def gui_remove_as_groupadmin_from_group(db: Session, authed_user, user_id,
                                        group_pk):
    if authed_user.admin:
        user = db.query(models.User).get(user_id)
        group = db.query(models.Group).get(group_pk)
        role = get_role_by_rolename(db=db, rolename='groupadmin')

        if user is not None and group is not None and role is not None:
            user_role_group = {
                'user_id': user_id,
                'group_id': group_pk,
                'user_group_role': get_role_by_rolename(db=db,
                                                        rolename='groupadmin').id
            }
            return delete_user_to_group(db=db,
                                        user_to_group=UserToGroup_Create.parse_obj(
                                            user_role_group))
        return
    return


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
