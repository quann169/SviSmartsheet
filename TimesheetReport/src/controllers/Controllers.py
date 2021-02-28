'''
Created on Feb 22, 2021

@author: toannguyen
'''
from src.models.smartsheet.SmartsheetModel import Sheet, Task, SmartSheets
from src.models.database.DatabaseModel import Configuration, Task, FinalTask
from src.commons.Enums import DbHeader, DbTable, ExcelHeader, SettingKeys, DefaulteValue
from src.commons.Message import MsgError, MsgWarning, Msg
from src.commons.Utils import search_pattern, message_generate, println, remove_path, split_patern
from flask import session
from pprint import pprint
import pandas as pd
import os, sys
import config


class Controllers:
    def __init__(self):
        pass
    
    def parse_smarsheet_and_update_task(self, list_sheet_id=None):
        cfg_obj = Configuration()
        sheet_info  = cfg_obj.get_sheet_config(list_sheet_id)
        list_sheet  = []
        for row in sheet_info:
            list_sheet.append((row[DbHeader.SHEET_NAME], row[DbHeader.LATEST_MODIFIED], int(row[DbHeader.SHEET_ID])))

        sms_obj = SmartSheets(list_sheet = list_sheet)
        sms_obj.connect_smartsheet()
        sms_obj.parse()
        config_obj  = Configuration()
        config_obj.get_all_user_information()
        user_info = config_obj.users
        task_obj    = Task()
        for sheet_name in sms_obj.info:
            # save children_task only
            
            child_tasks         = sms_obj.info[sheet_name].children_task
            sheet_id            = sms_obj.info[sheet_name].sheet_id
            latest_modified     = sms_obj.info[sheet_name].latest_modified
            is_parse            = sms_obj.info[sheet_name].is_parse
            if is_parse:
                
                task_obj.set_attr(sheet_id    = sheet_id)
                task_obj.remove_all_task_information_by_project_id()
                list_records_task   = []
                for child_task_obj in child_tasks:
                    sibling_id      = child_task_obj.sibling_id
                    parent_id       = child_task_obj.parent_id
                    self_id         = child_task_obj.self_id
                    task_name       = child_task_obj.task_name
                    dates           = child_task_obj.list_date
                    start_date      = child_task_obj.start_date
                    end_date        = child_task_obj.end_date
                    duration        = child_task_obj.duration
                    complete        = child_task_obj.complete
                    predecessors    = child_task_obj.predecessors
                    comments        = child_task_obj.comments
                    actual_end_date = child_task_obj.actual_end_date
                    status          = child_task_obj.status
                    is_children     = 1
                    allocation      = child_task_obj.allocation
                    assign_to       = child_task_obj.assign_to
                    try:
                        user_id = user_info[assign_to].user_id
                    except KeyError:
                        user_id = SettingKeys.NA_USER_ID
                    for date, week in dates:
                        record  = (
                            str(sheet_id),
                            str(user_id),
                            str(sibling_id),
                            str(parent_id),
                            str(self_id),
                            task_name,
                            date,
                            str(start_date),
                            str(end_date),
                            duration,
                            str(complete),
                            str(predecessors),
                            comments,
                            actual_end_date,
                            status,
                            str(is_children),
                            str(allocation)
                            )
                        list_records_task.append(record)
                task_obj.add_task(list_records_task)
                config_obj.set_attr(sheet_id            = sheet_id,
                                    latest_modified     = latest_modified)
                config_obj.update_latest_modified_of_sheet()
    
    def import_timeoff(self, file_name):
        try:
            file_path   = os.path.join(os.path.join(config.WORKING_PATH, 'upload'), file_name)
            df          = pd.read_excel (file_path, sheet_name='Time-Off', engine='openpyxl')
            
            config_obj  = Configuration()
            config_obj.get_all_user_information()
            users_info  = config_obj.users
            user_full_name_info = config_obj.users_full_name
            exist_id     = {}
            
            list_record = []
            for index in range(0, len(df[ExcelHeader.ID])):
                id_timeoff          = str(df[ExcelHeader.ID][index])
                try:
                    unuse = exist_id[id_timeoff]
                    message = message_generate(MsgWarning.W001, id_timeoff)
                    println(message, 'debug')
                    continue
                except KeyError:
                    exist_id[id_timeoff] = ''
                
                requester   = str(df[ExcelHeader.REQUESTER][index])
                department  = str(df[ExcelHeader.DEPARTMENT][index])
                type_leave  = str(df[ExcelHeader.TYPE][index])
                start_date  = str(df[ExcelHeader.START_DATE][index])
                end_date    = str(df[ExcelHeader.END_DATE][index])
                workday     = search_pattern(str(df[ExcelHeader.WORKDAYS][index]),'(.+?)\((.+?)h\)')[1]
                status      = str(df[ExcelHeader.STATUS][index])
                user_id     = SettingKeys.NA_USER_ID
                updated_by = 'root'
                try:
                    user_id = users_info[requester].user_id
                except KeyError:
                    try:
                        user_id = user_full_name_info[requester].user_id
                    except KeyError:
                        pass

                list_record.append(
                    (
                        id_timeoff, 
                        user_id, 
                        department,
                        type_leave,
                        start_date,
                        end_date,
                        workday,
                        status,
                        updated_by
                        )
                    )
            config_obj.remove_all_timeoff_information()
            config_obj.add_list_timeoff(list_record)
            remove_path(file_path)
            return 1, Msg.M001
        except Exception as e:
            println(e, 'exception')
            return 0, e
        
    def get_timeoff_info(self):
        config_obj  = Configuration()
        result      = config_obj.get_list_timeoff()
        return result
    
    def import_holiday(self, file_name):
        try:
            file_path   = os.path.join(os.path.join(config.WORKING_PATH, 'upload'), file_name)
            df          = pd.read_excel (file_path, sheet_name='Holiday', engine='openpyxl')
            config_obj  = Configuration()
            for index in range(0, len(df[ExcelHeader.HOLIDAY])):
                date          = str(df[ExcelHeader.HOLIDAY][index])
                if date not in SettingKeys.EMPTY_CELL:
                    if not config_obj.is_exist_holiday(date):
                        config_obj.add_holiday(date)
            return 1, Msg.M001
        except Exception as e:
            println(e, 'exception')
            return 0, e
    
    def get_session(self, key=None):
        try:
            val   = session[key]
            
            return val
        except KeyError:
            return None
        
    def get_holiday_info(self):
        config_obj  = Configuration()
        result      = config_obj.get_list_holiday()
        return result   
    
    def get_sheet_config(self):
        config_obj  = Configuration()
        result      = config_obj.get_sheet_config()
        return result    
    
    def update_session(self, key, val):
        try:
            session.pop(key, None)
            session[key] = val
            
            return 1, ''
        except Exception as e:
            println(e, 'exception')
            return 0, e
    
    def import_sheet(self, file_name):
        try:
            
            file_path   = os.path.join(os.path.join(config.WORKING_PATH, 'upload'), file_name)
            df          = pd.read_excel (file_path, sheet_name='Sheet', engine='openpyxl')
            config_obj  = Configuration()
            sheet_type  = config_obj.get_sheet_type_info()
            sheet_type_info = {}
            for row in sheet_type:
                sheet_type_id   = row[DbHeader.SHEET_TYPE_ID]
                sheet_type_name = row[DbHeader.SHEET_TYPE]
                sheet_type_info[sheet_type_name] = sheet_type_id
            
            sms_obj = SmartSheets()
            sms_obj.connect_smartsheet()
            available_sheet_name = sms_obj.available_name
            #validate sheet 
            for index in range(0, len(df[ExcelHeader.SHEET_NAME])):
                sheet_name          = str(df[ExcelHeader.SHEET_NAME][index])
                if sheet_name not in SettingKeys.EMPTY_CELL and sheet_name not in available_sheet_name:
                    message = message_generate(MsgError.E002, sheet_name)
                    println(message, 'error')
                    return  0, message
            config_obj.set_attr(updated_by  = 'root')
            for index in range(0, len(df[ExcelHeader.SHEET_NAME])):
                sheet_name          = str(df[ExcelHeader.SHEET_NAME][index])
                sheet_type          = str(df[ExcelHeader.SHEET_TYPE][index])
                if sheet_name not in SettingKeys.EMPTY_CELL:
                    try:
                        sheet_type_id  = sheet_type_info[sheet_type]
                    except KeyError:
                        sheet_type_id  = SettingKeys.NA_SHEET_TYPE_ID
                    users               = split_patern(str(df[ExcelHeader.RESOURCE][index]))
                    config_obj.set_attr(sheet_name      = sheet_name,
                                        sheet_type_id   = str(sheet_type_id),
                                        latest_modified = DefaulteValue.DATETIME)

                    if config_obj.is_exist_sheet():
                        config_obj.update_sheet()
                    else:
                        config_obj.add_sheet()
                
            return 1, Msg.M001
        except Exception as e:
            println(e, 'exception')
            return 0, e         
    
    def get_resource_config(self):
        config_obj  = Configuration()
        result      = config_obj.get_list_resource()
        return result    
                
    def import_resource(self, file_name):
        try:
            file_path   = os.path.join(os.path.join(config.WORKING_PATH, 'upload'), file_name)
            df          = pd.read_excel (file_path, sheet_name='Staff', engine='openpyxl')
            config_obj  = Configuration()
            eng_type  = config_obj.get_eng_type_info()
            eng_type_info = {}
            for row in eng_type:
                eng_type_id   = row[DbHeader.ENG_TYPE_ID]
                eng_type_name = row[DbHeader.ENG_TYPE_NAME]
                eng_type_info[eng_type_name] = eng_type_id
            
            
            eng_level  = config_obj.get_eng_level_info()
            eng_level_info = {}
            for row in eng_level:
                eng_level_id   = row[DbHeader.ENG_LEVEL_ID]
                eng_level_name = row[DbHeader.LEVEL]
                eng_level_info[eng_level_name] = eng_level_id


            teams  = config_obj.get_team_info()
            teams_info = {}
            for row in teams:
                team_id   = row[DbHeader.TEAM_ID]
                team_name = row[DbHeader.TEAM_NAME]
                lead_id   = row[DbHeader.TEAM_LEAD_ID]
                teams_info[team_name] = team_id
            
            config_obj.set_attr(updated_by  = 'root')
            for index in range(0, len(df[ExcelHeader.RESOURCE])):
                resource          = str(df[ExcelHeader.RESOURCE][index])
                eng_type          = str(df[ExcelHeader.ENG_TYPE][index])
                eng_level         = str(df[ExcelHeader.ENG_LEVEL][index])
                email             = str(df[ExcelHeader.EMAIL][index])
                full_name         = str(df[ExcelHeader.FULL_NAME][index])
                team              = str(df[ExcelHeader.TEAM][index])
                leader            = str(df[ExcelHeader.LEADER][index])
                is_active         = str(df[ExcelHeader.IS_ACTIVE][index])
                other_name        = str(df[ExcelHeader.OTHER_NAME][index])
                
                
                
                if resource not in SettingKeys.EMPTY_CELL:
                    try:
                        eng_type_id   = eng_type_info[eng_type]
                    except KeyError:
                        eng_type_id  = SettingKeys.NA_ENG_TYPE_ID
                    try:
                        eng_level_id  = eng_level_info[eng_level]
                    except KeyError:
                        eng_level_id  = SettingKeys.NA_ENG_LEVEL_ID
                    try:
                        team_id     = teams_info[team]
                    except KeyError:
                        team_id     = SettingKeys.NA_TEAM_ID
                        
                    if other_name in SettingKeys.EMPTY_CELL:
                        other_name  = ''
                    
                    config_obj.set_attr(user_name      = resource,
                                        eng_type_id   = str(eng_type_id),
                                        eng_level_id   = str(eng_level_id),
                                        team_id   = str(team_id),
                                        email   = str(email),
                                        full_name   = str(full_name),
                                        is_active   = str(is_active),
                                        other_name   = str(other_name))
                   
                    if config_obj.is_exist_resource():
                        config_obj.update_resource()
                    else:
                        config_obj.add_resource()
                
            return 1, Msg.M001
        except Exception as e:
            println(e, 'exception')
            return 0, e       