from classes.SheetDataValidator import Validator
from clients.GoogleClient import GoogleClient
from managers.DbUploadManager import UploadManager


validator = Validator()
validation_manager = validator.get_manager()
service = GoogleClient()
mc = UploadManager()

sheets = validation_manager.get_list_of_sheets()
for sheet in sheets:
    sheet_service_name = validation_manager.get_service_name_by_sheet_name(sheet)
    ranges = validation_manager.get_transformed_location(sheet_name=sheet)
    google_data = service.get(ranges)
    table = validation_manager.compile2table(google_data)

    validated = []

    for i in range(len(table)):
        validator.set_body(table[i])
        validator.set_kwargs(sheet_name=sheet)
        if not validator.is_ready():
            continue
        validator.process()
        if validator.get_result():
            validated.append([i, validator.get_body()])
        else:
            service.send_response(sheet, i, validator.get_message())
        validator.wipe()

    for valid in validated:
        temp = []
        for valid in validated:
            temp.append(valid[1])
        temp.pop(validated.index(valid))
        if valid[1] in temp:
            service.send_response(sheet, valid[0], "Нельзя загружать в базу данных записи с одинаковым ID. Смените ID")
            validated.pop(validated.index(valid))

    batch = []
    for valid in validated:
        service_field_names = validation_manager.get_list_of_service_field_names(sheet_name=sheet)
        split_data = mc.split_data(service_field_names, valid[1])
        db_batch = mc.search_in_db(sheet_service_name, split_data)
        if len(db_batch) == 0:
            service.send_response(sheet, valid[0], "Будет загружено в базу данных")
            batch.append(split_data)
        elif len(db_batch) == 1:
            if split_data == db_batch[0]:
                service.send_response(sheet, valid[0], "Запись есть в базе данных")
                batch.append(split_data)
            else:
                service.send_response(sheet, valid[0], "Запись с таким ID уже есть в базе. Смените ID")

    deploy = mc.get_difference_to_deploy(sheet_service_name, batch)
    delete = mc.get_difference_to_delete(sheet_service_name, batch)
    if len(deploy) > 0:
        for elem in deploy:
            mc.upload(sheet_service_name, elem)

    if len(delete) > 0:
       for elem in delete:
            mc.delete(sheet_service_name, elem)