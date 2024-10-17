def get_order_params(ordering):
    match ordering:
        case 'pk':
            return 'id asc'
        case '-pk':
            return 'id desc'
        case 'subject':
            return 'subject asc'
        case '-subject':
            return 'subject desc'
        case 'title':
            return 'title asc'
        case '-title':
            return 'title desc'
        case 'created_at':
            return 'created_at asc'
        case '-created_at':
            return 'created_at desc'
        case 'created_by':
            return 'created_by_id asc'
        case '-created_by':
            return 'created_by_id desc'
        case 'last_modified_at':
            return 'last_modified_at asc'
        case '-last_modified_at':
            return 'last_modified_at desc'
        case 'last_modified_by':
            return 'last_modified_by_id asc'
        case '-last_modified_by':
            return 'last_modified_by_id desc'
        case 'name':
            return 'name asc'
        case '-name':
            return 'name desc'
        case 'file_size':
            return 'file_size asc'
        case '-file_size':
            return 'file_size desc'
        case None:
            return 'id desc'
        case _:
            return 'id desc'
