__license__   = 'GPL v3'
__copyright__ = '2022 Mario Zimmermann <mail@zisoft.de>'
__docformat__ = 'restructuredtext en'

'''
PocketBook 632 Driver.
'''


from .device import Device



# CLI must come before Device as it implements the CLI functions that
# are inherited from the device interface in Device.
class POCKETBOOK632(Device):

    '''
    Class for PocketBook 632 drivers. Implements the logic for 
    managing the read status of books.
    This is a two-way sync. You can set the read status either on
    the device or in calibre (via a customized Y/N column '#read').
    The status will be synced to the device and vice-versa.
    '''

    name  = 'PocketBook Touch HD 3'
    gui_name = 'PocketBook'
    description    = _('Communicate with the PocketBook 632 readers')
    author         = 'Mario Zimmermann'
    supported_platforms = ['windows', 'osx', 'linux']
    # Ordered list of supported formats
    FORMATS     = ['epub', 'pdf', 'fb2', 'txt', 'pdf', 'html', 'djvu', 'doc', 'docx', 'rtf', 'chm']

    CAN_SET_METADATA = ['collections']

    FORMATS     = ['epub', 'pdf', 'fb2', 'txt', 'pdf', 'html', 'djvu', 'doc', 'docx', 'rtf', 'chm']
    VENDOR_ID   = [0xfffe]
    PRODUCT_ID  = [0x0001]
    BCD         = [0x0230, 0x101]

    EBOOK_DIR_MAIN = 'Books'
    SCAN_FROM_ROOT = True
    SUPPORTS_SUB_DIRS = True

    VENDOR_NAME = ['USB_2.0']
    WINDOWS_MAIN_MEM = WINDOWS_CARD_A_MEM = ['USB_FLASH_DRIVER']
