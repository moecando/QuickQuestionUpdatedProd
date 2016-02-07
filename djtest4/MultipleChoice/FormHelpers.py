from django.core.validators import validate_email, ValidationError

import re


class EmailListRegExes(object):

#     user_part_re = r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*$" r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"$)' # quoted-string
#     
#     dom_part_re =  r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}|[A-Z0-9-]{2,})$' r'|^\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$'
#     
    email_re = '[^,;\r\n\s]+@[^,;\r\n\s]+\.[^,;\r\n\s]+'
    
    
    #email_addr_with_header = '\s*(?:  (?:[A-Za-z\.\s\'0-9]*)  |  (?:"(?:[A-Za-z\.\s\'0-9\,]*)")    )\s*\<(?P<actual_address>%s)\>\w*' % email_re 
    email_addr_with_header = '\s*(?:  (?:[A-Za-z\.\s\'0-9]*)  |  (?:"(?:[A-Za-z\.\s\'0-9\,]*)")    )\s*\<(?:%s)\>\w*' % email_re 
    
    
    email_addr_with_header_or_without = '(%s |  %s)' % (email_re, email_addr_with_header)
    
    #list_of_emails_regex = '^(?:(?P<single_email>\s*(?P<email_address>%s))(?:[,;]|\r\n)+\s*)+$' % email_addr_with_header_or_without
    
    list_of_emails_regex = '^(?:(?P<single_email>\s*(?:%s))(?:[,;]|\r\n)+\s*)+$' % email_addr_with_header_or_without

    
    emails_for_extraction_with_find_all = '(?:(?:\s*(?P<the_email>%s))(?:[,;]|\r\n)+\s*)' % email_addr_with_header_or_without


def ValidateListOfEmailAddresses(list_of_addr):
    
    matches=re.match(EmailListRegExes.list_of_emails_regex, list_of_addr, re.IGNORECASE | re.VERBOSE)
    if matches != None:
        return True
    else:
        return False
    
    
def ValidateEmailAddressWithHeader(addr):
    if re.match(EmailListRegExes.email_addr_with_header, addr, re.IGNORECASE | re.VERBOSE) != None:
        return True
    else:
        return False

def ValidateEmailAddressWithOrWithoutHeader(addr):
    if re.match(EmailListRegExes.email_addr_with_header_or_without, addr, re.IGNORECASE | re.VERBOSE) != None:
        return True
    else:
        return False

    
    

def validate_email_addr_custom(addr):
    
    if re.match(EmailListRegExes.email_re, addr, re.IGNORECASE | re.VERBOSE) != None:
        return True
    else:
        return False

def ValidateListOfEmailAddressOld(list_of_addr):
    #try splitting on comma, semicolon and newlines
    #and validate each way
    
    
    #would better to use one giant regex but this is easier to write
    
    comma_split = list_of_addr.split(',')
    semi_colon_split = list_of_addr.split(';')
    dos_newline_split = list_of_addr.split('\r\n')
    unix_newline_split = list_of_addr.split('\n')
    
    
    is_one_list_valid = False
    
    for arr in [comma_split, semi_colon_split, dos_newline_split, unix_newline_split]:
        all_addresses_are_valid = True
        try:
            for addr in arr:
                #this check for None is a hack to allow for multiple delimeters
                #might sort of work
                if addr == '':
                    continue
                ValidateEmailAddress(addr.strip())
        except ValidationError:
            all_addresses_are_valid = False
        
        if all_addresses_are_valid == True:
            is_one_list_valid = True
            break

    if is_one_list_valid:
        return True
    else:
        return False
    
def ValidateEmailAddress(email_addr):
    bracketed_email_match_object=re.match('^\w*[A-Za-z\.\s\'0-9\"]*\<(?P<actual_address>.*)\>\w*$', email_addr)
    
    if bracketed_email_match_object != None:
        actual_email_addr = bracketed_email_match_object.group(1)
        validate_email(actual_email_addr)
    
    else:
        #OK so no brackets, just validate the whole thing after stripping for whitespace on both ends
        
        validate_email(email_addr.strip())
    
    return



def IsNonEmptyForm(f):
    return f.cleaned_data != {} and ('ans_text' in f.cleaned_data) and (f.cleaned_data['ans_text']).strip() != '' and (f.cleaned_data['DELETE'] == False)
