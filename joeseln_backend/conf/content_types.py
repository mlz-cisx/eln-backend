labbook_content_type = 10

element_content_type = 20

note_content_type = 30
note_content_type_version = 32

picture_content_type = 40
picture_content_type_version = 42

file_content_type = 50
file_content_type_version = 52

comment_content_type = 70
comment_content_type_version = 72

relation_content_type = 80
relation_content_type_version = 82

version_content_type = 60

labbook_content_type_model = 'labbooks.labbook'
element_content_type_model = 'labbooks.labbookchildelement'

note_content_type_model = 'shared_elements.note'
picture_content_type_model = 'pictures.picture'
file_content_type_model = 'shared_elements.file'
version_content_type_model = 'versions.version'
comment_content_type_model = 'shared_elements.comment'
relation_content_type_model = 'relations.relation'

type2model = {
    note_content_type: note_content_type_model,
    picture_content_type: picture_content_type_model,
    file_content_type: file_content_type_model,
    version_content_type: version_content_type_model,
    comment_content_type: comment_content_type_model,
    relation_content_type_model: relation_content_type_model
}
