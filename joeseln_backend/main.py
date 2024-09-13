import sys, os

# append path of parent dir to have joeseln_backend as module
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), os.pardir)))

import json
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from typing import Annotated
from datetime import timedelta

from typing import Any
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, WebSocket, \
    WebSocketDisconnect, Request, WebSocketException, Body, Depends, \
    HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from joeseln_backend.services.picture import picture_schemas, \
    picture_version_service, \
    picture_service
from joeseln_backend.services.note import note_schemas, note_service, \
    note_version_service
from joeseln_backend.services.labbookchildelements import \
    labbookchildelement_service, \
    labbookchildelement_schemas
from joeseln_backend.services.labbook import labbook_version_service
from joeseln_backend.services.labbook import labbook_schemas, labbook_service
from joeseln_backend.services.file import file_version_service, file_schemas, \
    file_service

from joeseln_backend.services.comment import comment_schemas, comment_service

from joeseln_backend.services.relation import relation_schemas

from joeseln_backend.services.user.user_schema import User
from joeseln_backend.database.database import SessionLocal
from joeseln_backend.export import export_labbook, export_note, export_picture, \
    export_file
from joeseln_backend.full_text_search import text_search
from joeseln_backend.conf.base_conf import ORIGINS, JAEGER_HOST, JAEGER_PORT, \
    JAEGER_SERVICE_NAME, STATIC_WS_TOKEN
from joeseln_backend.auth.security import Token, OAuth2PasswordBearer, \
    get_current_user, authenticate_user, \
    ACCESS_TOKEN_EXPIRE_SECONDS, \
    create_access_token
from joeseln_backend.ws.connection_manager import manager

# first logger
from joeseln_backend.mylogging.root_logger import logger

# second logger
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

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


@app.get("/health/")
def get_health():
    return ['ok']


@app.get("/labbooks/", response_model=list[labbook_schemas.Labbook])
def read_labbooks(request: Request,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    with jaeger_tracer.start_span('GET /labbooks/ user') as span:
        span.log_kv({'user': user.username})
    labbooks = labbook_service.get_labbooks_from_user(db=db,
                                                      params=request.query_params._dict,
                                                      user=user)
    return labbooks


@app.patch("/labbooks/{labbook_pk}", response_model=labbook_schemas.Labbook)
def patch_labbook(labbook: labbook_schemas.LabbookPatch,
                  labbook_pk: UUID,
                  db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    return labbook_service.patch_labbook(db=db, labbook_pk=labbook_pk,
                                         labbook=labbook, user=user)


@app.get("/labbooks/{labbook_pk}",
         response_model=labbook_schemas.labbook_with_privileges)
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


@app.get("/labbooks/{labbook_pk}/export/", response_class=FileResponse)
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


@app.get("/labbooks/{labbook_pk}/get_export_link/")
def export_link_labbook(labbook_pk: UUID,
                        db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    export_link = labbook_service.get_labbook_export_link(db=db,
                                                          labbook_pk=labbook_pk,
                                                          user=user)
    if export_link is None:
        raise HTTPException(status_code=404, detail="Labbook not found")
    return export_link


@app.post("/labbooks/", response_model=labbook_schemas.Labbook)
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


@app.get("/labbooks/{labbook_pk}/elements/",
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


@app.post("/labbooks/{labbook_pk}/elements/",
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
                               labbook_childelem=elem)
    return lb_element


@app.patch("/labbooks/{labbook_pk}/elements/{element_pk}/",
           response_model=labbookchildelement_schemas.Labbookchildelement)
async def patch_labbook_elem(
        labbook_pk: UUID,
        element_pk: UUID,
        elem: labbookchildelement_schemas.Labbookchildelement_Create,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # elements created by admin can't be touched
    lb_element = labbookchildelement_service. \
        patch_lb_childelement(db=db,
                              labbook_pk=labbook_pk,
                              element_pk=element_pk,
                              labbook_childelem=elem)
    return lb_element


@app.put("/labbooks/{labbook_pk}/elements/update_all/")
async def update_labbook_elements(
        labbook_pk: str,
        elems: list[labbookchildelement_schemas.Labbookchildelement_Update],
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # all groupmembers
    labbookchildelement_service. \
        update_all_lb_childelements(db=db,
                                    labbook_childelems=elems,
                                    labbook_pk=labbook_pk)
    return ['ok']


@app.get("/labbooks/{labbook_pk}/history/")
def get_labbook_history(
        request: Request,
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users
    logger.info(request.query_params._dict)
    return ['ok']


@app.get("/labbooks/{labbook_pk}/versions/",
         response_model=list[labbook_schemas.LabbookVersion])
def get_labbook_versions(
        request: Request,
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # for all users
    return labbook_version_service.get_all_labbook_versions(db=db,
                                                            labbook_pk=labbook_pk)


@app.post("/labbooks/{labbook_pk}/versions/",
          response_model=labbook_schemas.Labbook)
def add_labbook_version(
        summary: labbook_schemas.LabbookVersionSummary,
        labbook_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    return labbook_version_service.add_labbook_version(db=db,
                                                       labbook_pk=labbook_pk,
                                                       summary=summary.summary)


@app.post("/labbooks/{labbook_pk}/versions/{version_pk}/restore/")
def restore_labbook_version(
        labbook_pk: UUID,
        version_pk: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    return labbook_version_service.restore_labbook_version(db=db,
                                                           labbook_pk=labbook_pk,
                                                           version_pk=version_pk)


@app.get("/labbooks/{labbook_pk}/versions/{version_pk}/preview/",
         response_model=labbook_schemas.LabbookPreviewVersion)
def preview_labbook_version(
        labbook_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    # only for admins and groupadmins
    return labbook_version_service.get_labbook_version_metadata(db=db,
                                                                version_pk=version_pk)


@app.post("/notes/",
          response_model=note_schemas.Note)
def create_note(
        elem: note_schemas.NoteCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_service.create_note(db=db, note=elem)
    return db_note


@app.get("/notes/",
         response_model=list[note_schemas.Note])
def read_notes(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_notes = note_service.get_all_notes(db=db,
                                          params=request.query_params._dict)
    return db_notes


@app.patch("/notes/{note_pk}/",
           response_model=note_schemas.Note)
def patch_note(
        note_pk: UUID,
        elem: note_schemas.NoteCreate,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_service.update_note(db=db, note_pk=note_pk, note=elem)
    return db_note


@app.patch("/notes/{note_pk}/soft_delete/",
           response_model=note_schemas.Note)
def soft_delete_note(
        note_pk: UUID,
        labbook_data: labbookchildelement_schemas.Labbookchildelement_Delete,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_service.soft_delete_note(db=db, note_pk=note_pk,
                                            labbook_data=labbook_data)
    return db_note


@app.patch("/notes/{note_pk}/restore/",
           response_model=note_schemas.Note)
def restore_note(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_service.restore_note(db=db, note_pk=note_pk)
    return db_note


@app.get("/notes/{note_pk}/",
         response_model=note_schemas.Note)
def get_note(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_service.get_note(db=db, note_pk=note_pk)
    return db_note


@app.get("/notes/{note_pk}/export/",
         response_class=FileResponse)
def export_note_content(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_note = export_note.get_export_data(db=db, note_pk=note_pk,
                                                jwt=request.query_params._dict)
    return dwldable_note


@app.get("/notes/{note_pk}/get_export_link/")
def export_link__note(
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    export_link = note_service.get_note_export_link(db=db, note_pk=note_pk)
    return export_link


@app.get("/notes/{note_pk}/history/")
def get_note_history(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return ['ok']


@app.get("/notes/{note_pk}/versions/",
         response_model=list[note_schemas.NoteVersion])
async def get_note_versions(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return note_version_service.get_all_note_versions(db=db, note_pk=note_pk)


@app.post("/notes/{note_pk}/versions/", response_model=note_schemas.Note)
def add_note_version(
        summary: note_schemas.NoteVersionSummary,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_version_service.add_note_version(db=db,
                                                    note_pk=note_pk,
                                                    summary=summary.summary)[0]
    return db_note


@app.post("/notes/{note_pk}/versions/{version_pk}/restore/")
async def restore_note_version(
        note_pk: UUID,
        version_pk: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_note = note_version_service.restore_note_version(db=db, note_pk=note_pk,
                                                        version_pk=version_pk)
    return db_note


@app.get("/notes/{note_pk}/versions/{version_pk}/preview/",
         response_model=note_schemas.NotePreviewVersion)
async def preview_note_version(
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return note_version_service.get_note_version_metadata(db=db,
                                                          version_pk=version_pk)


@app.get("/notes/{note_pk}/relations/",
         response_model=list[relation_schemas.Relation])
def get_note_relations(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    return note_service.get_note_relations(db=db, note_pk=note_pk,
                                           params=request.query_params._dict)


@app.post("/notes/{note_pk}/relations/")
def add_note_relation(
        request: Request,
        note_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    logger.info(request.query_params._dict)
    return ['ok']


@app.put("/notes/{note_pk}/relations/{relation_pk}/")
def put_note_relation(
        request: Request,
        note_pk: UUID,
        relation_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    logger.info(request.query_params._dict)
    return ['ok']


@app.delete("/notes/{note_pk}/relations/{relation_pk}/")
def delete_note_relation(
        request: Request,
        note_pk: UUID,
        relation_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    note_service.delete_note_relation(db=db, note_pk=note_pk, relation_pk=relation_pk)
    return ['ok']


@app.post("/pictures/", response_model=picture_schemas.Picture)
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
                                                                   contents=contents)
        # sketch upload
        elif 'rendered_image' in form.keys():
            contents = await form['rendered_image'].read()
            ret_vals = picture_service.process_sketch_upload_form(form=form,
                                                                  db=db,
                                                                  contents=contents)

        return ret_vals


@app.get("/pictures/", response_model=list[picture_schemas.Picture])
def read_pictures(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pictures = picture_service.get_all_pictures(db=db,
                                                   params=request.query_params._dict)
    return db_pictures


@app.get("/pictures/{picture_pk}/",
         response_model=picture_schemas.Picture)
def get_picture(
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_picture = picture_service.get_picture(db=db, picture_pk=picture_pk)

    return db_picture


# TODO check if this is secure: user auth will be done with request.query_params._dict
@app.get("/pictures/{picture_pk}/bi_download/",
         response_class=FileResponse)
def get_bi_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db)):
    logger.info(request.query_params._dict)
    bi_picture = picture_service.build_bi_download_response(
        picture_pk=picture_pk,
        db=db,
        jwt=request.query_params._dict)
    return bi_picture


# TODO check if this is secure: user auth will be done with request.query_params._dict
@app.get("/pictures/{picture_pk}/ri_download/",
         response_class=FileResponse)
def get_ri_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db)):
    logger.info(request.query_params._dict)
    ri_picture = picture_service.build_ri_download_response(
        picture_pk=picture_pk,
        db=db,
        jwt=request.query_params._dict)
    return ri_picture


# TODO check if this is secure: user auth will be done with request.query_params._dict
@app.get("/pictures/{picture_pk}/shapes/",
         response_class=FileResponse)
def get_shapes(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db)):
    logger.info(request.query_params._dict)
    shapes = picture_service.build_shapes_response(picture_pk=picture_pk, db=db,
                                                   jwt=request.query_params._dict)
    return shapes


@app.get("/pictures/{picture_pk}/export/",
         response_class=FileResponse)
def export_picture_content(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_pic = export_picture.get_export_data(db=db, picture_pk=picture_pk,
                                                  jwt=request.query_params._dict)
    return dwldable_pic


@app.get("/pictures/{picture_pk}/get_export_link/")
def export_link_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    export_link = picture_service.get_picture_export_link(db=db,
                                                          picture_pk=picture_pk)

    return export_link


@app.patch("/pictures/{picture_pk}/soft_delete/",
           response_model=picture_schemas.Picture)
def soft_delete_picture(
        picture_pk: UUID,
        labbook_data: labbookchildelement_schemas.Labbookchildelement_Delete,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pic = picture_service.soft_delete_picture(db=db, picture_pk=picture_pk,
                                                 labbook_data=labbook_data)
    return db_pic


@app.patch("/pictures/{picture_pk}/restore/",
           response_model=picture_schemas.Picture)
def restore_picture(
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_pic = picture_service.restore_picture(db=db, picture_pk=picture_pk)
    return db_pic


@app.patch("/pictures/{picture_pk}/",
           response_model=picture_schemas.Picture)
async def patch_picture(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    async with request.form() as form:
        bi_img_contents = await form['background_image'].read()
        ri_img_contents = await form['rendered_image'].read()
        shapes_contents = await form['shapes_image'].read()
        db_picture = picture_service.update_picture(pk=picture_pk,
                                                    db=db,
                                                    form=form,
                                                    bi_img_contents=bi_img_contents,
                                                    ri_img_contents=ri_img_contents,
                                                    shapes_contents=shapes_contents)
        return db_picture


@app.get("/pictures/{picture_pk}/history/")
def get_picture_history(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return ['ok']


@app.get("/pictures/{picture_pk}/versions/",
         response_model=list[picture_schemas.PictureVersion])
def get_picture_versions(
        request: Request,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return picture_version_service.get_all_picture_versions(db=db,
                                                            picture_pk=picture_pk)


@app.post("/pictures/{picture_pk}/versions/",
          response_model=picture_schemas.Picture)
def add_picture_version(
        summary: picture_schemas.PictureVersionSummary,
        picture_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return picture_version_service.add_picture_version(db=db,
                                                       picture_pk=picture_pk,
                                                       summary=summary.summary)[
        0]


@app.post("/pictures/{picture_pk}/versions/{version_pk}/restore/")
def restore_picture_version(
        picture_pk: UUID,
        version_pk: str,
        payload: Any = Body(None),
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_picture = picture_version_service.restore_picture_version(db=db,
                                                                 picture_pk=picture_pk,
                                                                 version_pk=version_pk)
    return db_picture


@app.get("/pictures/{picture_pk}/versions/{version_pk}/preview/",
         response_model=picture_schemas.PicturePreviewVersion)
def preview_picture_version(
        picture_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return picture_version_service.get_picture_version_metadata(db=db,
                                                                version_pk=version_pk)


@app.post("/files/", response_model=file_schemas.File)
async def UploadFile(request: Request,
                     db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    # logger.info(user)
    async with request.form() as form:
        contents = await form['path'].read()
        ret_vals = file_service.process_file_upload_form(form=form, db=db,
                                                         contents=contents)

        return ret_vals


@app.get("/files/",
         response_model=list[file_schemas.File])
def read_files(
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_files = file_service.get_all_files(db=db,
                                          params=request.query_params._dict)

    return db_files


@app.patch("/files/{file_pk}", response_model=file_schemas.File)
def patch_file(
        elem: file_schemas.FilePatch,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    file_reponse = file_service.update_file(file_pk=file_pk, db=db, elem=elem)
    return file_reponse


@app.get("/files/{file_pk}", response_model=file_schemas.File)
def get_file(
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    file_reponse = file_service.get_file(db=db, file_pk=file_pk)
    return file_reponse


@app.get("/files/{file_pk}/download",
         response_class=FileResponse)
def download_file(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_file = file_service.build_file_download_response(file_pk=file_pk,
                                                              db=db,
                                                              jwt=request.query_params._dict)

    return dwldable_file


@app.get("/files/{file_pk}/export",
         response_class=FileResponse)
def export_file_content(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    dwldable_file = export_file.get_export_data(db=db, file_pk=file_pk,
                                                jwt=request.query_params._dict)

    return dwldable_file


@app.get("/files/{file_pk}/get_export_link/")
def export_link_file(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    export_link = file_service.get_file_export_link(db=db, file_pk=file_pk)
    return export_link


@app.patch("/files/{file_pk}/soft_delete/",
           response_model=file_schemas.File)
def soft_delete_file(
        file_pk: UUID,
        labbook_data: labbookchildelement_schemas.Labbookchildelement_Delete,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_file = file_service.soft_delete_file(db=db, file_pk=file_pk,
                                            labbook_data=labbook_data)
    return db_file


@app.patch("/files/{file_pk}/restore/",
           response_model=file_schemas.File)
def restore_file(
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_file = file_service.restore_file(db=db, file_pk=file_pk)
    return db_file


@app.get("/files/{file_pk}/history/")
def get_file_history(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return ['ok']


@app.get("/files/{file_pk}/versions/",
         response_model=list[file_schemas.FileVersion])
def get_file_versions(
        request: Request,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return file_version_service.get_all_file_versions(db=db, file_pk=file_pk)


@app.post("/files/{file_pk}/versions/", response_model=file_schemas.File)
def add_file_version(
        summary: file_schemas.FileVersionSummary,
        file_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return file_version_service.add_file_version(db=db, file_pk=file_pk,
                                                 summary=summary.summary)[0]


@app.post("/files/{file_pk}/versions/{version_pk}/restore/")
def restore_file_version(
        file_pk: UUID,
        version_pk: str,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    db_file = file_version_service.restore_file_version(db=db, file_pk=file_pk,
                                                        version_pk=version_pk)
    return db_file


@app.get("/files/{file_pk}/versions/{version_pk}/preview/",
         response_model=file_schemas.FilePreviewVersion)
def preview_file_version(
        file_pk: UUID,
        version_pk: UUID,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    # logger.info(user)
    return file_version_service.get_file_version_metadata(db=db,
                                                          version_pk=version_pk)


@app.post("/comments/")
def create_comment(
        comment: comment_schemas.CreateComment,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    logger.info(user)
    return comment_service.create_comment(db=db, comment=comment)


@app.websocket("/ws/elements/")
async def websocket_endpoint(*, websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # logger.info(data)
            if data['auth'] == STATIC_WS_TOKEN:
                token = data['auth']
                # we don't want to transmit any token from backend !
                del data['auth']
                await manager.broadcast_json(message=data)
            elif data['auth'] and '__zone_symbol__value' in json.loads(
                    json.dumps(data['auth'])):
                # handling keycloak
                token = json.loads(json.dumps(data['auth']))[
                    '__zone_symbol__value']
            else:
                # handling jwt auth
                token = data['auth']
            if token and token != STATIC_WS_TOKEN:
                # TODO do ws authentication here
                pass
            else:
                WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info('ws elements disconnected')

    except KeyError:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)


@app.get('/users/me', response_model=User)
async def user_me(user: User = Depends(get_current_user)):
    logger.info(user.username)
    return user


@app.post("/token")
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


@app.get("/search/")
def eln_search(request: Request,
               db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    # logger.info(user)
    result = text_search.search_with_model(db=db,
                                           model=request.query_params._dict[
                                               'model'],
                                           search_text=
                                           request.query_params._dict[
                                               'search'])
    return result
