import math
import uuid
from datetime import datetime
import time

from io import StringIO
# from fpdf import FPDF
import re
import csv
import logging

import stark_core

name = "STARK Utilities"

def compose_report_operators_and_parameters(key, data, metadata):
    composed_filter_dict = {"filter_string":"","expression_values": {}}
    if data['operator'] == "IN":
        string_split = data['value'].split(',')
        composed_filter_dict['filter_string'] += f" {key} IN "
        temp_in_string = ""
        in_string = ""
        in_counter = 1
        composed_filter_dict['report_params'] = {key : f"Is in {data['value']}"}
        for in_index in string_split:
            in_string += f" :inParam{in_counter}, "
            composed_filter_dict['expression_values'][f":inParam{in_counter}"] = {data['type'] : in_index.strip()}
            in_counter += 1
        temp_in_string = in_string[1:-2]
        composed_filter_dict['filter_string'] += f"({temp_in_string}) AND"
    elif data['operator'] in [ "contains", "begins_with" ]:
        composed_filter_dict['filter_string'] += f" {data['operator']}({key}, :{key}) AND"
        composed_filter_dict['expression_values'][f":{key}"] = {data['type'] : data['value'].strip()}
        composed_filter_dict['report_params'] = {key : f"{data['operator'].capitalize().replace('_', ' ')} {data['value']}"}
    elif data['operator'] == "between":
        from_to_split = data['value'].split(',')
        composed_filter_dict['filter_string'] += f" ({key} BETWEEN :from{key} AND :to{key}) AND"
        composed_filter_dict['expression_values'][f":from{key}"] = {data['type'] : from_to_split[0].strip()}
        composed_filter_dict['expression_values'][f":to{key}"] = {data['type'] : from_to_split[1].strip()}
        composed_filter_dict['report_params'] = {key : f"Between {from_to_split[0].strip()} and {from_to_split[1].strip()}"}
    else:
        if key != 'pk':
            if metadata[key]['data_type'] == 'list':
                if data['operator'] == '=':
                    composed_filter_dict['filter_string'] += f" contains({key}, :{key}) AND"
                elif data['operator'] == '<>':
                    composed_filter_dict['filter_string'] += f" not contains({key}, :{key}) AND"
            else:
                composed_filter_dict['filter_string'] += f" {key} {data['operator']} :{key} AND"
        else: 
            composed_filter_dict['filter_string'] += f" {key} {data['operator']} :{key} AND"
        
        composed_filter_dict['expression_values'][f":{key}"] = {data['type'] : data['value'].strip()}
        
        operator_string_equivalent = ""
        if data['operator'] == '=':
            operator_string_equivalent = 'Is equal to'
        elif data['operator'] == '>':
            operator_string_equivalent = 'Is greater than'
        elif data['operator'] == '>=':
            operator_string_equivalent = 'Is greater than or equal to'
        elif data['operator'] == '<':
            operator_string_equivalent = 'Is less than'
        elif data['operator'] == '<=':
            operator_string_equivalent = 'Is less than or equal to'
        elif data['operator'] == '<>':
            operator_string_equivalent = 'Is not equal to'
        else:
            operator_string_equivalent = 'Invalid operator'
        composed_filter_dict['report_params'] = {key : f" {operator_string_equivalent} {data['value'].strip()}" }

    return composed_filter_dict

def az_compose_report_operators_and_parameters(key, data, metadata):
    logging.info(key)
    if key == "pk":
        key = "_id"
    logging.info(f"new key {key}")
    
    composed_filter_dict = {
        "operators" : [{
            'STARK-Is-Deleted' : {'$exists': False}
        }],
        "report_params": {}
    }
    if data['operator'] == "IN":
        composed_filter_dict["operators"].append({ key : {'$in' : data['value']}})
        composed_filter_dict['report_params'] = {key : f"Is in {data['value']}"}
        
    elif data['operator'] == "contains":
        composed_filter_dict["operators"].append({ key : {'$text' : data['value'].strip()}})
        composed_filter_dict['report_params'] = {key : f"{data['operator'].capitalize().replace('_', ' ')} {data['value']}"}

    elif data['operator'] ==  "begins_with":
        regex_pattern = re.compile("^" + re.escape(data['value'].strip()))
        composed_filter_dict["operators"].append({ key : {'$regex' : regex_pattern}})
        composed_filter_dict['report_params'] = {key : f"{data['operator'].capitalize().replace('_', ' ')} {data['value']}"}

    elif data['operator'] == "between":
        from_to_split = data['value'].split(',')
        between_dict = {
            '$gte' : from_to_split[0].strip(),
            '$lte' : from_to_split[1].strip()
        }
        composed_filter_dict["operators"].append({ key : between_dict})
        composed_filter_dict['report_params'] = {key : f"Between {from_to_split[0].strip()} and {from_to_split[1].strip()}"}
    else:
        # if key != 'pk':
        #     if metadata[key]['data_type'] == 'list':
        #         if data['operator'] == '=':
        #             composed_filter_dict['filter_string'] += f" contains({key}, :{key}) AND"
        #         elif data['operator'] == '<>':
        #             composed_filter_dict['filter_string'] += f" not contains({key}, :{key}) AND"
        #     else:
        #         composed_filter_dict['filter_string'] += f" {key} {data['operator']} :{key} AND"
        # else: 
        #     composed_filter_dict['filter_string'] += f" {key} {data['operator']} :{key} AND"
        
        # composed_filter_dict['expression_values'][f":{key}"] = {data['type'] : data['value'].strip()}

        clean_value = data['value'].strip()
        operator_string_equivalent = ""
        if data['operator'] == '=':
            composed_filter_dict["operators"].append({ key : clean_value})
            operator_string_equivalent = 'Is equal to'
        elif data['operator'] == '>':
            composed_filter_dict["operators"].append({ key : {'$gt' : clean_value}})
            operator_string_equivalent = 'Is greater than'
        elif data['operator'] == '>=':
            composed_filter_dict["operators"].append({ key : {'$gte' : clean_value}})
            operator_string_equivalent = 'Is greater than or equal to'
        elif data['operator'] == '<':
            composed_filter_dict["operators"].append({ key : {'$lt' : clean_value}})
            operator_string_equivalent = 'Is less than'
        elif data['operator'] == '<=':
            composed_filter_dict["operators"].append({ key : {'$lte' : clean_value}})
            operator_string_equivalent = 'Is less than or equal to'
        elif data['operator'] == '<>':
            composed_filter_dict["operators"].append({ key : {'$ne' : clean_value}})
            operator_string_equivalent = 'Is not equal to'
        else:
            operator_string_equivalent = 'Invalid operator'
        composed_filter_dict['report_params'] = {key : f" {operator_string_equivalent} {data['value'].strip()}" }

    return composed_filter_dict

def filter_criteria_for_many_fields(str_value, criteria):

    if criteria['operator'] not in ['IN', 'between']:
        criteria_value = convert_value_data_type(criteria['value'], criteria['data_type'])
        compare_value = convert_value_data_type(str_value, criteria['data_type'])

    is_data_included = False

    if str_value != "":
        if criteria['operator'] == '=':
            if compare_value == criteria_value:
                is_data_included = True

        elif criteria['operator'] == '<>':
            if compare_value != criteria_value:
                is_data_included = True

        elif criteria['operator'] == '<':
            if  compare_value < criteria_value:
                is_data_included = True

        elif criteria['operator'] == '<=':
            if compare_value <= criteria_value:
                is_data_included = True

        elif criteria['operator'] == '>':
            if compare_value > criteria_value:
                is_data_included = True

        elif criteria['operator'] == '>=':
            if compare_value >= criteria_value:
                is_data_included = True

        elif criteria['operator'] == 'contains':
            if  criteria_value in compare_value:
                is_data_included = True

        elif criteria['operator'] == 'IN':
            if str(str_value) != "" and str(str_value) in criteria_value:
                is_data_included = True

        elif criteria['operator'] == 'begins_with':
            if str(str_value).startswith(criteria['value']):
                is_data_included = True

        elif criteria['operator'] == 'between':
            between_values = criteria['value'].split(',')
            first_value = str(between_values[0]).strip()
            second_value = str(between_values[1]).strip()
            
            converted_first_value   = convert_value_data_type(first_value, criteria['data_type'])
            converted_second_value  = convert_value_data_type(second_value, criteria['data_type'])
            converted_compare_value = convert_value_data_type(str_value, criteria['data_type'])
            
            if converted_first_value <= converted_compare_value <= converted_second_value:
                is_data_included = True

    return is_data_included

def filter_report_list(report_list, diff_list):
    for rows in report_list:
        for index in diff_list:
            rows.pop(index)
    
    return report_list

def create_csv(report_list, csv_header):
    
    file_buff = StringIO()
    writer = csv.DictWriter(file_buff, fieldnames=csv_header,quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for rows in report_list:
        writer.writerow(rows)

    filename = f"{str(uuid.uuid4())}"
    csv_file = f"{filename}.csv"
    
    return csv_file, file_buff.getvalue()

def prepare_pdf_data(data_to_tuple, master_fields, report_params, metadata, pk_field):
    #FIXME: PDF GENERATOR: can be outsourced to a layer, for refining 
    master_fields.insert(0, '#')
    numerical_columns = {}
    for key, items in metadata.items():
        if items['data_type'] == 'number':
            numerical_columns.update({key: 0})
    row_list = []
    counter = 1 
    for key in data_to_tuple:
        column_list = []
        for index in master_fields:
            if(index != '#'):
                if index in numerical_columns.keys():
                    numerical_columns[index] += int(key[index])
                column_list.append(key[index])
        column_list.insert(0, str(counter)) 
        row_list.append(tuple(column_list))
        counter += 1

    if len(numerical_columns) > 0:
        column_list = []
        for values in master_fields:
            if values in numerical_columns:
                column_list.append(str(numerical_columns.get(values, '')))
            else:
                column_list.append('')
        row_list.append(column_list)

    header_tuple = tuple(master_fields) 
    data_tuple = tuple(row_list)

    filename = f"{str(uuid.uuid4())}"
    pdf_file = f"{filename}.pdf"

    # pdf = create_pdf(header_tuple, data_tuple, report_params, pk_field, metadata)

    # return pdf_file, pdf.output()
    return pdf_file, {}


# def create_pdf(header_tuple, data_tuple, report_params, pk_field, metadata):

#     pdf = FPDF(orientation='L')
#     pdf.add_page()
#     pdf.set_font("Helvetica", size=10)
#     with_total_row = False
#     line_height = pdf.font_size * 2.5
#     row_number_width = 10
#     col_width = pdf.epw / len(header_tuple)  # distribute content evenly
#     col_width = col_width + (col_width - row_number_width) / (len(header_tuple) -1)

#     render_page_header(pdf, line_height, report_params, pk_field)
#     render_table_header(pdf, header_tuple, col_width, line_height, row_number_width) 
    
#     for index in header_tuple:
#         if index != "#" and ("Count of" not in index and "Sum of" not in index):
#             if metadata[index.replace(" ","_")]["data_type"] == 'number':
#                 with_total_row = True

#     counter = 0
#     for row in data_tuple:
#         if pdf.will_page_break(line_height):
#             render_table_header(pdf, header_tuple, col_width, line_height, row_number_width) 
#         row_height = pdf.font_size * estimate_lines_needed(pdf, row, col_width)
#         if row_height < line_height: #min height
#             row_height = line_height
#         elif row_height > 120: #max height tested, beyond this value will distort the table
#             row_height = 120

#         if counter % 2 ==0:
#             pdf.set_fill_color(222,226,230)
#         else:
#             pdf.set_fill_color(255,255,255)
        
#         if with_total_row and counter + 1 == len(data_tuple):
#             border = 'T'
#         else:
#             border = 0

#         column_counter = 0
#         for datum in row:
#             width = col_width
#             if column_counter == 0:
#                 width = row_number_width
#                 text_align = 'R'
#             else:
#                 if ("Count of" not in header_tuple[column_counter] and "Sum of" not in header_tuple[column_counter]): 
#                     if metadata[header_tuple[column_counter].replace(" ","_")]['data_type'] in ['number', 'date']:
#                         text_align = 'R'
#                     else:
#                         text_align = 'L'
#                 else:
#                     text_align = 'R'

#             pdf.multi_cell(width, row_height, str(datum), border=border, new_x="RIGHT", new_y="TOP", max_line_height=pdf.font_size, fill = True, align = text_align)
#             column_counter += 1
#         pdf.ln(row_height)
#         counter += 1

#     return pdf

def render_table_header(pdf, header_tuple, col_width, line_height, row_number_width):
    pdf.set_font(style="B")  # enabling bold text
    pdf.set_fill_color(52, 58,64)
    pdf.set_text_color(255,255,255)
    row_header_line_height = line_height * 1.5
    for col_name in header_tuple:
        if col_name == '#':
            width = row_number_width
        else:
            width = col_width

        pdf.multi_cell(width, row_header_line_height, col_name, border='TB', align='C',
                new_x="RIGHT", new_y="TOP",max_line_height=pdf.font_size, fill=True)
    pdf.ln(row_header_line_height)
    pdf.set_font(style="")  # disabling bold text
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(0, 0, 0)

def render_page_header(pdf, line_height, report_params, pk_field):
    param_width = pdf.epw / 4
    #Report Title
    pdf.set_font("Helvetica", size=14, style="B")
    pdf.multi_cell(0,line_height, "Customer Report", 0, 'C',
                    new_x="RIGHT", new_y="TOP", max_line_height=pdf.font_size)
    pdf.ln()

    #Report Parameters
    newline_print_counter = 1
    pdf.set_font("Helvetica", size=12, style="B")
    pdf.multi_cell(0,line_height, "Report Parameters:", 0, "L", new_x="RIGHT", new_y="TOP", max_line_height=pdf.font_size)
    pdf.ln(pdf.font_size *1.5)
    if len(report_params) > 0:
        pdf.set_font("Helvetica", size=10)
        for key, value in report_params.items():
            if key == 'pk':
                key = pk_field
            pdf.multi_cell(30,line_height, key.replace("_", " "), 0, "L", new_x="RIGHT", new_y="TOP", max_line_height=pdf.font_size)
            pdf.multi_cell(param_width,line_height, value, 0, "L", new_x="RIGHT", new_y="TOP", max_line_height=pdf.font_size)
            if newline_print_counter == 2:
                pdf.ln(pdf.font_size *1.5)
                newline_print_counter = 0
            newline_print_counter += 1
    else:
        pdf.multi_cell(30,line_height, "N/A", 0, "L", new_x="RIGHT", new_y="TOP", max_line_height=pdf.font_size)
    pdf.ln()


def estimate_lines_needed(self, iter, col_width: float) -> int:
    font_width_in_mm = (
        self.font_size_pt * 0.33 * 0.6
    )  # assumption: a letter is half his height in width, the 0.6 is the value you want to play with
    max_cell_text_len_header = max([len(str(col)) for col in iter])  # how long is the longest string?
    return math.ceil(max_cell_text_len_header * font_width_in_mm / col_width)

# def save_object_to_bucket(body, filename, bucket_name = None, directory = "tmp"):
#     canned_ACL = 'private'
#     if bucket_name == None:
#         bucket_name = stark_core.bucket_name
#         canned_ACL = 'public-read'

#     s3_action = s3.put_object(
#         ACL= canned_ACL,
#         Body= body,
#         Bucket=bucket_name,
#         Key=directory+'/'+filename
#     )

# def copy_object_to_bucket(filename, destination_dir, bucket_name = None, source_dir='tmp'):
#     if bucket_name == None:
#         bucket = stark_core.bucket_name

#         copy_source = {
#             'Bucket': bucket,
#             'Key': source_dir + '/' + filename
#         }

#         extra_args = {
#             'ACL': 'public-read'
#         }
#         s3_res.meta.client.copy(copy_source, bucket, destination_dir + filename, extra_args)

def convert_value_data_type(value, data_type):
    converted_value = ""
    if value != "":
        if data_type == 'date':
            converted_value = datetime.strptime(value, '%Y-%m-%d').date()
        elif data_type == 'float':
            converted_value = float(value)
        elif data_type == 'integer':
            converted_value = int(value)
        else:
            #str default
            converted_value = str(value)

    return converted_value

def append_record_metadata(transaction_type, user ):
    metadata = {}
    timestamp = int(time.time())
    if transaction_type == 'add':
        #append in item
        metadata['STARK-Created-By'] = {'S': user}
        metadata['STARK-Created-TS'] = {'N': str(timestamp)}
        
    elif transaction_type == 'edit':
        metadata[':STARKUpdatedBy'] = {'S': user}
        metadata[':STARKUpdatedTS'] = {'N': str(timestamp)}

    elif transaction_type == 'delete':
        ttl_value = timestamp + stark_core.TTL_for_deleted_records_in_days * 24 * 60 * 60
        metadata[':STARKDeletedBy'] = {'S': user}
        metadata[':STARKDeletedTS'] = {'N': str(timestamp)}
        metadata[':STARKIsDeleted'] = {'S': 'Y'}
        metadata[':ttl'] = {'N': str(ttl_value)}

    return metadata  

def az_append_record_metadata(transaction_type, user ):
    metadata = {}
    timestamp = int(time.time())
    if transaction_type == 'add':
        #append in item
        metadata['STARK-Created-By'] = user
        metadata['STARK-Created-TS'] = str(timestamp)
        
    elif transaction_type == 'edit':
        metadata['STARK-Updated-By'] =  user
        metadata['STARK-Updated-TS'] = str(timestamp)

    elif transaction_type == 'delete':
        ttl_value = timestamp + stark_core.TTL_for_deleted_records_in_days * 24 * 60 * 60
        metadata['STARK-Deleted-By'] = user
        metadata['STARK-Deleted-TS'] = str(timestamp)
        metadata['STARK-Is-Deleted'] =  'Y'
        metadata['TTL'] = str(ttl_value)

    return metadata
