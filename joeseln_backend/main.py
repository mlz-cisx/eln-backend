import sys, os

# append path of parent dir to have joeseln_backend as module
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), os.pardir)))

from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from typing import Annotated
from datetime import timedelta

from typing import Any
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Request, Body, Depends, \
    HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from joeseln_backend.services.picture import picture_schemas, \
    picture_version_service, \
    picture_service
from joeseln_backend.services.note import note_schemas, note_service, \
    note_version_service
from joeseln_backend.services.admin_user import admin_user_service
from joeseln_backend.services.user import user_service
from joeseln_backend.services.user_to_group import user_to_group_service, \
    user_to_group_schema
from joeseln_backend.services.labbookchildelements import \
    labbookchildelement_service, \
    labbookchildelement_schemas
from joeseln_backend.services.labbook import labbook_version_service
from joeseln_backend.services.labbook import labbook_schemas, labbook_service
from joeseln_backend.services.file import file_version_service, file_schemas, \
    file_service

from joeseln_backend.services.comment import comment_schemas, comment_service

from joeseln_backend.services.relation import relation_schemas
from joeseln_backend.services.history import history_schema
from joeseln_backend.services.history.history_service import get_history

from joeseln_backend.services.role.basic_roles_creator import \
    create_basic_roles, create_inital_admin

from joeseln_backend.services.user.user_schema import User, PasswordChange, \
    UserExtended, UserWithPrivileges, GuiUserCreate, AdminExtended, \
    GroupUserExtended, GuiUserPatch, PasswordPatch, UserExtendedConnected
from joeseln_backend.services.user.user_password import gui_password_change, \
    gui_patch_user_password, guicreate_user

from joeseln_backend.services.admin_stat.admin_stat_service import get_stat
from joeseln_backend.services.admin_stat.admin_stat_schemas import StatResponse

from joeseln_backend.database.database import SessionLocal
from joeseln_backend.export import export_labbook, export_note, export_picture, \
    export_file
from joeseln_backend.full_text_search import text_search
from joeseln_backend.conf.base_conf import ORIGINS, JAEGER_HOST, JAEGER_PORT, \
    JAEGER_SERVICE_NAME, CENTRIFUGO_JWT_KEY, CENTRIFUGO_CHANNEL
from joeseln_backend.auth.security import Token, OAuth2PasswordBearer, \
    get_current_user, authenticate_user, \
    ACCESS_TOKEN_EXPIRE_SECONDS, \
    create_access_token

# first logger
from joeseln_backend.mylogging.root_logger import logger

# second logger
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

import jwt
import time

trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({SERVICE_NAME: JAEGER_SERVICE_NAME})))
tracer_provider = trace.get_tracer_provider()
jaeger_exporter = JaegerExporter(agent_host_name=JAEGER_HOST,
                                 agent_port=JAEGER_PORT)
tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

# third logger
from joeseln_backend.mylogging.jaeger_logger import jaeger_tracer

jaeger_tracer = jaeger_tracer()

# will create all tables if not exist
from joeseln_backend.models.table_creator import table_creator

table_creator()
create_basic_roles()
create_inital_admin()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

origins = ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Test(BaseModel):
    test: str


oauth2_scheme_alter = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/api/health/")
def get_health():
    return ['ok']


@app.get("/api/stat", response_model=StatResponse)
def read_stat(db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    stats = get_stat(db, user)
    if stats is None:
        raise HTTPException(status_code=204, detail="Not Authorized")
    return stats


@app.get("/api/labbooks/", response_model=list[labbook_schemas.LabbookWithLen])
def read_labbooks(request: Request,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    with jaeger_tracer.start_span('GET /labbooks/ user') as span:
        span.log_kv({'user': user.username})
    labbooks = labbook_service.get_labbooks_from_user(db=db,
                                                      params=request.query_params._dict,
                                                      user=user)
    return labbooks


@app.patch("/api/labbooks/{labbook_pk}", response_model=labbook_schemas.Labbook)
def patch_labbook(labbook: labbook_schemas.LabbookPatch,
                  labbook_pk: UUID,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    return labbook_service.patch_labbook(db=db, labbook_pk=labbook_pk,
                                         labbook=labbook, user=user)


@app.get("/api/labbooks/{labbook_pk}",
         response_model=labbook_schemas.LabbookWithPrivileges)
def read_labbook(labbook_pk: UUID,
                 db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    # logger.info(user)
    labbook = labbook_service.get_labbook_with_privileges(db=db,
                                                          labbook_pk=labbook_pk,
                                                          user=user)
    if labbook is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return labbook


@app.get("/api/labbooks/{labbook_pk}/export/", response_class=FileResponse)
def export_labbook_content(request: Request, labbook_pk: UUID,
                           db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)):
    dwldable_labbook = export_labbook.get_export_data(db=db, lb_pk=labbook_pk,
                                                      jwt=
                                                      request.query_params._dict
                                                      ['jwt'])
    if dwldable_labbook is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return dwldable_labbook


@app.get("/api/labbooks/{labbook_pk}/get_export_link/")
def export_link_labbook(labbook_pk: UUID,
                        db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    export_link = labbook_service.get_labbook_export_link(db=db,
                                                          labbook_pk=labbook_pk,
                                                          user=user)
    if export_link is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return export_link


@app.post("/api/labbooks/", response_model=labbook_schemas.Labbook)
def create_labbook(labbook: labbook_schemas.LabbookCreate,
                   db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins
    new_lb = labbook_service.create_labbook(db=db, labbook=labbook, user=user)
    if new_lb:
        return new_lb
    else:
        raise HTTPException(status_code=404, detail="Labbook not found")


@app.patch("/api/labbooks/{labbook_pk}/soft_delete/",
           response_model=labbook_schemas.Labbook)
def soft_delete_labbook(
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # admin notes can only be deleted  by admins or groupadmins
    db_labbook = labbook_service.gui_soft_delete_labbook(db=db,
                                                         labbook_uuid=labbook_pk,
                                                         user=user)
    if db_labbook is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_labbook


@app.patch("/api/labbooks/{labbook_pk}/restore/",
           response_model=labbook_schemas.Labbook)
def restore_labbook(
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_labbook = labbook_service.gui_restore_labbook(db=db,
                                                     labbook_uuid=labbook_pk,
                                                     user=user)
    if db_labbook is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_labbook


@app.get("/api/labbooks/{labbook_pk}/elements/",
         response_model=list[labbookchildelement_schemas.Labbookchildelement])
def read_labbook_elems(labbook_pk: UUID,
                       db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    # logger.info(user)
    lb_elements = labbookchildelement_service.get_lb_childelements_from_user(
        db=db,
        labbook_pk=labbook_pk,
        as_export=False, user=user)
    if lb_elements is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return lb_elements


@app.post("/api/labbooks/{labbook_pk}/elements/",
          response_model=labbookchildelement_schemas.Labbookchildelement)
async def create_labbook_elem(
        labbook_pk: UUID,
        elem: labbookchildelement_schemas.Labbookchildelement_Create,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # all groupmembers
    lb_element = labbookchildelement_service. \
        create_lb_childelement(db=db, labbook_pk=labbook_pk,
                               labbook_childelem=elem, user=user)
    if lb_element is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return lb_element


@app.patch("/api/labbooks/{labbook_pk}/elements/{element_pk}/",
           response_model=labbookchildelement_schemas.Labbookchildelement)
async def patch_labbook_elem(
        labbook_pk: UUID,
        element_pk: UUID,
        elem: labbookchildelement_schemas.Labbookchildelement_Create,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    lb_element = labbookchildelement_service. \
        patch_lb_childelement(db=db,
                              labbook_pk=labbook_pk,
                              element_pk=element_pk,
                              labbook_childelem=elem,
                              user=user)
    if lb_element is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return lb_element


@app.put("/api/labbooks/{labbook_pk}/elements/update_all/")
async def update_labbook_elements(
        labbook_pk: str,
        elems: list[labbookchildelement_schemas.Labbookchildelement_Update],
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # all groupmembers
    if labbookchildelement_service. \
            update_all_lb_childelements(db=db,
                                        labbook_childelems=elems,
                                        labbook_pk=labbook_pk,
                                        user=user):
        return ['ok']
    else:
        raise HTTPException(status_code=404, detail="Labbook not found")


@app.get("/api/labbooks/{labbook_pk}/history/",
         response_model=list[history_schema.ElemHistory])
def get_labbook_history(
        request: Request,
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users
    return get_history(db=db, elem_id=labbook_pk, user=user)


@app.get("/api/labbooks/{labbook_pk}/versions/",
         response_model=list[labbook_schemas.LabbookVersion])
def get_labbook_versions(
        request: Request,
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users
    versions = labbook_version_service.get_all_labbook_versions(db=db,
                                                                labbook_pk=labbook_pk,
                                                                user=user)
    if versions is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return versions


@app.post("/api/labbooks/{labbook_pk}/versions/",
          response_model=labbook_schemas.Labbook)
def add_labbook_version(
        summary: labbook_schemas.LabbookVersionSummary,
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    lb_added = labbook_version_service.add_labbook_version(db=db,
                                                           labbook_pk=labbook_pk,
                                                           summary=summary.summary,
                                                           user=user)
    if lb_added is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return lb_added
    # DONE


@app.post("/api/labbooks/{labbook_pk}/versions/{version_pk}/restore/")
def restore_labbook_version(
        labbook_pk: UUID,
        version_pk: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    lb_restored = labbook_version_service.restore_labbook_version(db=db,
                                                                  labbook_pk=labbook_pk,
                                                                  version_pk=version_pk,
                                                                  user=user)
    if lb_restored is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return lb_restored


@app.get("/api/labbooks/{labbook_pk}/versions/{version_pk}/preview/",
         response_model=labbook_schemas.LabbookPreviewVersion)
def preview_labbook_version(
        labbook_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    lb_metadata = labbook_version_service.get_labbook_version_metadata(
        db=db,
        version_pk=version_pk,
        labbook_pk=labbook_pk,
        user=user)
    if lb_metadata is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return lb_metadata


@app.post("/api/notes/",
          response_model=note_schemas.Note)
def create_note(
        elem: note_schemas.NoteCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users
    db_note = note_service.create_note(db=db, note=elem, user=user)
    return db_note


@app.get("/api/notes/",
         response_model=list[note_schemas.NoteWithLbTitle])
def read_notes(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users with corresponding labbook access
    db_notes = note_service.get_all_notes(db=db,
                                          params=request.query_params._dict,
                                          user=user)
    return db_notes


@app.patch("/api/notes/{note_pk}/",
           response_model=note_schemas.Note)
def patch_note(
        note_pk: UUID,
        elem: note_schemas.NoteCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # admin notes can only be patched by admins
    db_note = note_service.update_note(db=db, note_pk=note_pk, note=elem,
                                       user=user)

    if db_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_note


@app.patch("/api/notes/{note_pk}/soft_delete/",
           response_model=note_schemas.Note)
def soft_delete_note(
        note_pk: UUID,
        labbook_data: labbookchildelement_schemas.Labbookchildelement_Delete,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # admin notes can only be deleted  by admins or groupadmins
    db_note = note_service.soft_delete_note(db=db, note_pk=note_pk,
                                            labbook_data=labbook_data,
                                            user=user)
    if db_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_note


@app.patch("/api/notes/{note_pk}/restore/",
           response_model=note_schemas.Note)
def restore_note(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # admin notes can only be restored  by admins or groupadmins
    db_note = note_service.restore_note(db=db, note_pk=note_pk, user=user)
    if db_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_note


@app.get("/api/notes/{note_pk}/",
         response_model=note_schemas.NoteWithPrivileges)
def get_note(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_service.get_note_with_privileges(db=db, note_pk=note_pk,
                                                    user=user)
    if db_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_note


@app.get("/api/notes/{note_pk}/export/",
         response_class=FileResponse)
def export_note_content(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_note = export_note.get_export_data(db=db, note_pk=note_pk,
                                                jwt=request.query_params._dict
                                                ['jwt'])
    if dwldable_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return dwldable_note


@app.get("/api/notes/{note_pk}/get_export_link/")
def export_link__note(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    export_link = note_service.get_note_export_link(db=db, note_pk=note_pk,
                                                    user=user)
    if export_link is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return export_link


@app.get("/api/notes/{note_pk}/history/",
         response_model=list[history_schema.ElemHistory])
def get_note_history(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return get_history(db=db, elem_id=note_pk, user=user)


@app.get("/api/notes/{note_pk}/versions/",
         response_model=list[note_schemas.NoteVersion])
async def get_note_versions(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    note_versions = note_version_service.get_all_note_versions(db=db,
                                                               note_pk=note_pk,
                                                               user=user)
    if note_versions is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return note_versions


@app.post("/api/notes/{note_pk}/versions/", response_model=note_schemas.Note)
def add_note_version(
        summary: note_schemas.NoteVersionSummary,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_version_service.add_note_version(db=db,
                                                    note_pk=note_pk,
                                                    summary=summary.summary,
                                                    user=user)[0]
    if db_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_note


@app.post("/api/notes/{note_pk}/versions/{version_pk}/restore/")
async def restore_note_version(
        note_pk: UUID,
        version_pk: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_version_service.restore_note_version(db=db, note_pk=note_pk,
                                                        version_pk=version_pk,
                                                        user=user)
    if db_note is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_note


@app.get("/api/notes/{note_pk}/versions/{version_pk}/preview/",
         response_model=note_schemas.NotePreviewVersion)
async def preview_note_version(
        note_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    version_metadata = note_version_service.get_note_version_metadata(db=db,
                                                                      note_pk=note_pk,
                                                                      version_pk=version_pk,
                                                                      user=user)

    if version_metadata is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return version_metadata


@app.get("/api/notes/{note_pk}/relations/",
         response_model=list[relation_schemas.Relation])
def get_note_relations(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    return note_service.get_note_relations(db=db, note_pk=note_pk,
                                           params=request.query_params._dict,
                                           user=user)


@app.post("/api/notes/{note_pk}/relations/")
def add_note_relation(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    logger.info(request.query_params._dict)
    return ['ok']
    # DONE not in use


@app.put("/api/notes/{note_pk}/relations/{relation_pk}/")
def put_note_relation(
        request: Request,
        note_pk: UUID,
        relation_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    logger.info(request.query_params._dict)
    return ['ok']
    # DONE not in use


@app.delete("/api/notes/{note_pk}/relations/{relation_pk}/")
def delete_note_relation(
        request: Request,
        note_pk: UUID,
        relation_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    note_rel = note_service.delete_note_relation(db=db, note_pk=note_pk,
                                                 relation_pk=relation_pk,
                                                 user=user)

    if note_rel is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return note_rel


@app.post("/api/pictures/", response_model=picture_schemas.Picture)
async def UploadImage(request: Request,
                      db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    # logger.info(user)
    async with request.form() as form:
        # picture upload
        if 'background_image' in form.keys():
            contents = await form['background_image'].read()
            ret_vals = picture_service.process_picture_upload_form(form=form,
                                                                   db=db,
                                                                   contents=contents,
                                                                   user=user)
        # sketch upload
        elif 'rendered_image' in form.keys():
            contents = await form['rendered_image'].read()
            ret_vals = picture_service.process_sketch_upload_form(form=form,
                                                                  db=db,
                                                                  contents=contents,
                                                                  user=user)

        return ret_vals


@app.get("/api/pictures/",
         response_model=list[picture_schemas.PictureWithLbTitle])
def read_pictures(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pictures = picture_service.get_all_pictures(db=db,
                                                   params=request.query_params._dict,
                                                   user=user)
    return db_pictures


@app.get("/api/pictures/{picture_pk}/",
         response_model=picture_schemas.PictureWithPrivileges)
def get_picture(
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_picture = picture_service.get_picture_with_privileges(db=db,
                                                             picture_pk=picture_pk,
                                                             user=user)
    return db_picture


@app.get("/api/pictures/{picture_pk}/bi_download/",
         response_class=FileResponse)
def get_bi_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db)):
    logger.info(request.query_params._dict)
    bi_picture = picture_service.build_bi_download_response(
        picture_pk=picture_pk,
        db=db,
        jwt=request.query_params._dict['jwt'])
    if bi_picture is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return bi_picture


@app.get("/api/pictures/{picture_pk}/ri_download/",
         response_class=FileResponse)
def get_ri_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db)):
    logger.info(request.query_params._dict)
    ri_picture = picture_service.build_ri_download_response(
        picture_pk=picture_pk,
        db=db,
        jwt=request.query_params._dict['jwt'])
    if ri_picture is None:
        raise HTTPException(status_code=404, detail="token expired")
    return ri_picture


@app.get("/api/pictures/{picture_pk}/shapes/",
         response_class=FileResponse)
def get_shapes(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db)):
    shapes = picture_service.build_shapes_response(picture_pk=picture_pk, db=db,
                                                   jwt=
                                                   request.query_params._dict[
                                                       'jwt'])
    if shapes is None:
        raise HTTPException(status_code=404, detail="token expired")
    return shapes


@app.get("/api/pictures/{picture_pk}/export/",
         response_class=FileResponse)
def export_picture_content(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_pic = export_picture.get_export_data(db=db, picture_pk=picture_pk,
                                                  jwt=request.query_params._dict
                                                  ['jwt'])
    if dwldable_pic is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return dwldable_pic


@app.get("/api/pictures/{picture_pk}/get_export_link/")
def export_link_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    export_link = picture_service.get_picture_export_link(db=db,
                                                          picture_pk=picture_pk,
                                                          user=user)
    if export_link is None:
        raise HTTPException(status_code=404, detail="Labbook not found")

    return export_link


@app.patch("/api/pictures/{picture_pk}/soft_delete/",
           response_model=picture_schemas.Picture)
def soft_delete_picture(
        picture_pk: UUID,
        labbook_data: labbookchildelement_schemas.Labbookchildelement_Delete,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pic = picture_service.soft_delete_picture(db=db, picture_pk=picture_pk,
                                                 labbook_data=labbook_data,
                                                 user=user)
    if db_pic is None:
        raise HTTPException(status_code=404, detail="Labbook not found")

    return db_pic


@app.patch("/api/pictures/{picture_pk}/restore/",
           response_model=picture_schemas.Picture)
def restore_picture(
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pic = picture_service.restore_picture(db=db, picture_pk=picture_pk,
                                             user=user)
    if db_pic is None:
        raise HTTPException(status_code=404, detail="Labbook not found")

    return db_pic


@app.patch("/api/pictures/{picture_pk}/task/",
           response_model=picture_schemas.Picture)
def restore_picture(
        pic_payload: picture_schemas.UpdatePictureTitle,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pic = picture_service.update_title(db=db, picture_pk=picture_pk,
                                          user=user, pic_payload=pic_payload)
    if db_pic is None:
        raise HTTPException(status_code=404, detail="Labbook not found")

    return db_pic


@app.patch("/api/pictures/{picture_pk}/",
           response_model=picture_schemas.Picture)
async def patch_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users
    async with request.form() as form:
        bi_img_contents = await form['background_image'].read()
        ri_img_contents = await form['rendered_image'].read()
        shapes_contents = await form['shapes_image'].read()
        db_picture = picture_service.update_picture(pk=picture_pk,
                                                    db=db,
                                                    form=form,
                                                    bi_img_contents=bi_img_contents,
                                                    ri_img_contents=ri_img_contents,
                                                    shapes_contents=shapes_contents,
                                                    user=user)

        if db_picture is None:
            raise HTTPException(status_code=404, detail="Labbook not found")

        return db_picture


@app.get("/api/pictures/{picture_pk}/history/",
         response_model=list[history_schema.ElemHistory])
def get_picture_history(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return get_history(db=db, elem_id=picture_pk, user=user)


@app.get("/api/pictures/{picture_pk}/versions/",
         response_model=list[picture_schemas.PictureVersion])
def get_picture_versions(
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    picture_versions = picture_version_service.get_all_picture_versions(db=db,
                                                                        picture_pk=picture_pk,
                                                                        user=user)
    if picture_versions is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return picture_versions


@app.post("/api/pictures/{picture_pk}/versions/",
          response_model=picture_schemas.Picture)
def add_picture_version(
        summary: picture_schemas.PictureVersionSummary,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    picture_version = picture_version_service.add_picture_version(db=db,
                                                                  picture_pk=picture_pk,
                                                                  summary=summary.summary,
                                                                  user=user)[
        0]

    if picture_version is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return picture_version


@app.post("/api/pictures/{picture_pk}/versions/{version_pk}/restore/")
def restore_picture_version(
        picture_pk: UUID,
        version_pk: str,
        payload: Any = Body(None),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_picture = picture_version_service.restore_picture_version(db=db,
                                                                 picture_pk=picture_pk,
                                                                 version_pk=version_pk,
                                                                 user=user)
    if db_picture is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_picture


@app.get("/api/pictures/{picture_pk}/versions/{version_pk}/preview/",
         response_model=picture_schemas.PicturePreviewVersion)
def preview_picture_version(
        picture_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    version_metadata = picture_version_service.get_picture_version_metadata(
        db=db,
        picture_pk=picture_pk,
        version_pk=version_pk,
        user=user)

    if version_metadata is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return version_metadata


@app.get("/api/pictures/{picture_pk}/relations/",
         response_model=list[relation_schemas.Relation])
def get_picture_relations(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    return picture_service.get_picture_relations(db=db, picture_pk=picture_pk,
                                                 params=request.query_params._dict,
                                                 user=user)


@app.delete("/api/pictures/{picture_pk}/relations/{relation_pk}/")
def delete_picture_relation(
        request: Request,
        picture_pk: UUID,
        relation_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    picture_service.delete_picture_relation(db=db, picture_pk=picture_pk,
                                            relation_pk=relation_pk, user=user)
    return ['ok']


@app.post("/api/files/", response_model=file_schemas.File)
async def UploadFile(request: Request,
                     db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    # logger.info(user)
    async with request.form() as form:
        contents = await form['path'].read()
        ret_vals = file_service.process_file_upload_form(form=form, db=db,
                                                         contents=contents,
                                                         user=user)

        return ret_vals


@app.get("/api/files/",
         response_model=list[file_schemas.FileWithLbTitle])
def read_files(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_files = file_service.get_all_files(db=db,
                                          params=request.query_params._dict,
                                          user=user)

    return db_files


@app.patch("/api/files/{file_pk}", response_model=file_schemas.File)
def patch_file(
        elem: file_schemas.FilePatch,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    file_reponse = file_service.update_file(file_pk=file_pk, db=db, elem=elem,
                                            user=user)
    if file_reponse is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return file_reponse


@app.get("/api/files/{file_pk}", response_model=file_schemas.FileWithPrivileges)
def get_file(
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    file_response = file_service.get_file_with_privileges(db=db,
                                                          file_pk=file_pk,
                                                          user=user)
    return file_response


@app.get("/api/files/{file_pk}/download",
         response_class=FileResponse)
def download_file(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_file = file_service.build_file_download_response(file_pk=file_pk,
                                                              db=db,
                                                              jwt=
                                                              request.query_params._dict[
                                                                  'jwt'])

    if dwldable_file is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return dwldable_file


@app.get("/api/files/{file_pk}/export",
         response_class=FileResponse)
def export_file_content(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_file = export_file.get_export_data(db=db, file_pk=file_pk,
                                                jwt=request.query_params._dict
                                                ['jwt'])
    if dwldable_file is None:
        raise HTTPException(status_code=404, detail="Labbook not found")

    return dwldable_file


@app.get("/api/files/{file_pk}/get_export_link/")
def export_link_file(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    export_link = file_service.get_file_export_link(db=db, file_pk=file_pk,
                                                    user=user)
    if export_link is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return export_link


@app.patch("/api/files/{file_pk}/soft_delete/",
           response_model=file_schemas.File)
def soft_delete_file(
        file_pk: UUID,
        labbook_data: labbookchildelement_schemas.Labbookchildelement_Delete,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_file = file_service.soft_delete_file(db=db, file_pk=file_pk,
                                            labbook_data=labbook_data,
                                            user=user)
    if db_file is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_file


@app.patch("/api/files/{file_pk}/restore/",
           response_model=file_schemas.File)
def restore_file(
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_file = file_service.restore_file(db=db, file_pk=file_pk, user=user)
    if db_file is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_file


@app.get("/api/files/{file_pk}/history/",
         response_model=list[history_schema.ElemHistory])
def get_file_history(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return get_history(db=db, elem_id=file_pk, user=user)


@app.get("/api/files/{file_pk}/versions/",
         response_model=list[file_schemas.FileVersion])
def get_file_versions(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    file_versions = file_version_service.get_all_file_versions(db=db,
                                                               file_pk=file_pk,
                                                               user=user)
    if file_versions is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return file_versions


@app.post("/api/files/{file_pk}/versions/", response_model=file_schemas.File)
def add_file_version(
        summary: file_schemas.FileVersionSummary,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    file_version = file_version_service.add_file_version(db=db, file_pk=file_pk,
                                                         summary=summary.summary,
                                                         user=user)[0]
    if file_version is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return file_version


@app.post("/api/files/{file_pk}/versions/{version_pk}/restore/")
def restore_file_version(
        file_pk: UUID,
        version_pk: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_file = file_version_service.restore_file_version(db=db, file_pk=file_pk,
                                                        version_pk=version_pk,
                                                        user=user)
    if db_file is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_file


@app.get("/api/files/{file_pk}/versions/{version_pk}/preview/",
         response_model=file_schemas.FilePreviewVersion)
def preview_file_version(
        file_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    version_metadata = file_version_service.get_file_version_metadata \
        (db=db,
         file_pk=file_pk,
         version_pk=version_pk,
         user=user)

    if version_metadata is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return version_metadata


@app.get("/api/files/{file_pk}/relations/",
         response_model=list[relation_schemas.Relation])
def get_file_relations(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    return file_service.get_file_relations(db=db, file_pk=file_pk,
                                           params=request.query_params._dict,
                                           user=user)


@app.delete("/api/files/{file_pk}/relations/{relation_pk}/")
def delete_file_relation(
        request: Request,
        file_pk: UUID,
        relation_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    file_service.delete_file_relation(db=db, file_pk=file_pk,
                                      relation_pk=relation_pk, user=user)
    return ['ok']


@app.post("/api/comments/")
def create_comment(
        comment: comment_schemas.CreateComment,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_comment = comment_service.create_comment(db=db, comment=comment,
                                                user=user)
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_comment


@app.get("/api/contrifugo/token")
def generate_contrifugo_jwt(user: User = Depends(get_current_user)):
    claims = {"sub": str(user.id), "exp": int(time.time()) + 3600}
    connect_token = jwt.encode(claims, CENTRIFUGO_JWT_KEY,
                               algorithm='HS256').decode()

    claims = {"sub": str(user.id), "channel": CENTRIFUGO_CHANNEL,
              "exp": int(time.time()) + 3600}
    subscribe_token = jwt.encode(claims, CENTRIFUGO_JWT_KEY,
                                 algorithm='HS256').decode()

    return {"connect_token": connect_token, "subscribe_token": subscribe_token}


@app.get('/api/users/me', response_model=User)
async def user_me(user: User = Depends(get_current_user)):
    return user


@app.put('/api/change_password')
def change_password(password: PasswordChange,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_user),
                    ):
    db_user = gui_password_change(db=db, user=user,
                                  none_hashed_password=password)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return ['ok']


@app.post("/api/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends(),],
        db: Session = Depends(get_db),
) -> Token:
    user = authenticate_user(db=db, username=form_data.username,
                             password=form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    # we align to keycloak's sub
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/api/search/")
def eln_search(request: Request,
               db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    # logger.info(user)
    result = text_search.search_with_model(db=db,
                                           model=request.query_params._dict[
                                               'model'],
                                           search_text=
                                           request.query_params._dict[
                                               'search'], user=user)
    return result


@app.get("/api/admin/users", response_model=list[UserExtendedConnected])
def get_users(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_users = admin_user_service.get_all_users(db=db,
                                                params=request.query_params._dict,
                                                user=user)
    if db_users is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_users


@app.post("/api/admin/users", response_model=UserExtended)
def create_user(
        user_to_create: GuiUserCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = guicreate_user(db=db, user=user,
                             user_to_create=user_to_create)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.get("/api/admin/users/{user_id}", response_model=UserWithPrivileges)
def get_user(
        user_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = admin_user_service.get_user_by_id(db=db, user=user,
                                                user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.patch("/api/admin/users/{user_id}", response_model=UserExtended)
def patch_user(
        user_id: int,
        user_to_patch: GuiUserPatch,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = user_service.gui_patch_user(db=db,
                                          authed_user=user,
                                          user_id=user_id,
                                          user_to_patch=user_to_patch)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.patch("/api/admin/users/{user_id}/foo", response_model=UserExtended)
def patch_user_password(
        user_id: int,
        password_to_patch: PasswordPatch,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = gui_patch_user_password(db=db,
                                      authed_user=user,
                                      user_id=user_id,
                                      password_to_patch=password_to_patch)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.patch("/api/admin/users/{user_id}/soft_delete/")
def soft_delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = admin_user_service.soft_delete_user(db=db,
                                                  user_id=user_id,
                                                  user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.patch("/api/admin/users/{user_id}/restore/")
def restore_user(
        user_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = admin_user_service.restore_user(db=db,
                                              user_id=user_id,
                                              user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.get("/api/admin/admins", response_model=list[AdminExtended])
def get_admins(request: Request,
               db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    db_users = admin_user_service.get_all_admins(db=db,
                                                 params=request.query_params._dict,
                                                 user=user)
    if db_users is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_users


@app.patch("/api/admin/admins/{user_id}/soft_delete/",
           response_model=AdminExtended)
def soft_delete_admin(
        user_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = admin_user_service.remove_as_admin(db=db,
                                                 user_id=user_id,
                                                 user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.patch("/api/admin/admins/{user_id}/restore/", response_model=AdminExtended)
def restore_admin(
        user_id: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user = admin_user_service.set_as_admin(db=db,
                                              user_id=user_id,
                                              user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user


@app.get("/api/admin/groups",
         response_model=list[user_to_group_schema.ExtendedGroup])
def get_groups(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_groups = user_to_group_service.get_all_groups(db=db,
                                                     params=request.query_params._dict,
                                                     user=user)
    if db_groups is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_groups


@app.get("/api/admin/groups/{group_pk}")
def get_group(
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    title = user_to_group_service.get_groupname(db=db,
                                                group_pk=group_pk,
                                                user=user)
    if title is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return [title]


@app.patch("/api/admin/groups/{group_pk}/soft_delete/")
def delete_group(
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    message = user_to_group_service.gui_delete_group(db=db,
                                                     authed_user=user,
                                                     group_pk=group_pk)
    if message is None:
        raise HTTPException(status_code=404, detail="Delete Error")
    return message


@app.post("/api/admin/groups", response_model=user_to_group_schema.Group)
def create_group(
        group_to_create: user_to_group_schema.Group_Create,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_group = user_to_group_service.gui_create_group(db=db,
                                                      user=user,
                                                      group=group_to_create)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_group


@app.get("/api/admin/group/groupadmins/{group_pk}",
         response_model=list[GroupUserExtended])
def get_group_groupadmins(
        request: Request,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_groups = user_to_group_service.get_all_groupadmins(db=db,
                                                          group_pk=group_pk,
                                                          params=request.query_params._dict,
                                                          authed_user=user)
    if db_groups is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_groups


@app.patch("/api/admin/group/groupadmins/{group_pk}/{user_id}/soft_delete/")
def soft_delete_groupadmin(
        user_id: int,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user_to_group = user_to_group_service.gui_remove_as_groupadmin_from_group(
        db=db,
        group_pk=group_pk,
        user_id=user_id,
        authed_user=user)
    if db_user_to_group is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user_to_group


@app.patch("/api/admin/group/groupadmins/{group_pk}/{user_id}/restore/")
def restore_groupadmin(
        user_id: int,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user_to_group = user_to_group_service.gui_add_as_groupadmin_to_group(
        db=db,
        group_pk=group_pk,
        user_id=user_id,
        authed_user=user)
    if db_user_to_group is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user_to_group


@app.get("/api/admin/group/groupusers/{group_pk}",
         response_model=list[GroupUserExtended])
def get_group_users(request: Request,
                    group_pk: UUID,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    db_groups = user_to_group_service.get_all_groupusers(db=db,
                                                         group_pk=group_pk,
                                                         params=request.query_params._dict,
                                                         authed_user=user)
    if db_groups is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_groups


@app.patch("/api/admin/group/groupusers/{group_pk}/{user_id}/soft_delete/")
def soft_delete_group_user(
        user_id: int,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user_to_group = user_to_group_service.gui_remove_as_user_from_group(
        db=db,
        group_pk=group_pk,
        user_id=user_id,
        authed_user=user)
    if db_user_to_group is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user_to_group


@app.patch("/api/admin/group/groupusers/{group_pk}/{user_id}/restore/")
def restore_group_user(
        user_id: int,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user_to_group = user_to_group_service.gui_add_as_user_to_group(db=db,
                                                                      group_pk=group_pk,
                                                                      user_id=user_id,
                                                                      authed_user=user)
    if db_user_to_group is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return db_user_to_group

@app.get("/api/admin/group/groupguests/{group_pk}",
         response_model=list[GroupUserExtended])
def get_group_guests(request: Request,
                    group_pk: UUID,
                    db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    db_groups = user_to_group_service.get_all_groupguests(db=db,
                                                         group_pk=group_pk,
                                                         params=request.query_params._dict,
                                                         authed_user=user)
    if db_groups is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_groups


@app.patch("/api/admin/group/groupguests/{group_pk}/{user_id}/soft_delete/")
def soft_delete_group_guest(
        user_id: int,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user_to_group = user_to_group_service.gui_remove_as_guest_from_group(
        db=db,
        group_pk=group_pk,
        user_id=user_id,
        authed_user=user)
    if db_user_to_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_user_to_group


@app.patch("/api/admin/group/groupguests/{group_pk}/{user_id}/restore/")
def add_group_guests(
        user_id: int,
        group_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    db_user_to_group = user_to_group_service.gui_add_as_guest_to_group(db=db,
                                                                      group_pk=group_pk,
                                                                      user_id=user_id,
                                                                      authed_user=user)
    if db_user_to_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_user_to_group
