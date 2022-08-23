__license__   = 'GPL v3'
__copyright__ = '2022 Mario Zimmermann <mail@zisoft.de>'
__docformat__ = 'restructuredtext en'

'''
PocketBook Improved Driver.
'''

from calibre.devices.usbms.deviceconfig import DeviceConfig


class PocketBookImprovedDeviceConfig(DeviceConfig):

    EXTRA_CUSTOMIZATION_MESSAGE = [
        _('The Pocketbook supports to mark a book as read. Enter the lookup ' +
        'name of the custom Yes/No column:'),
    ]

    EXTRA_CUSTOMIZATION_DEFAULT = [
        '#read',
    ]

    OPT_READ_LOOKUP_NAME = 0
