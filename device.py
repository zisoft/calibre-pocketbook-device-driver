__license__   = 'GPL v3'
__copyright__ = '2022 Mario Zimmermann <mail@zisoft.de>'
__docformat__ = 'restructuredtext en'

'''
PocketBook Improved Driver.
'''

import os, time, json, shutil
import sqlite3 as sqlite
from contextlib import closing
import calibre
import traceback
# from itertools import cycle

from calibre.devices.usbms.driver import USBMS, debug_print

from calibre_plugins.pocketbook632.deviceconfig import PocketBookImprovedDeviceConfig



class POCKETBOOK_IMPROVED(USBMS, PocketBookImprovedDeviceConfig):

    '''
    PocketBook Improved Device Driver
    '''

    name  = 'PocketBook Improved Device Interface'
    gui_name = 'PocketBook Improved'
    description    = _('Communicate with PocketBook readers')
    author         = 'Mario Zimmermann'
    version        = (1, 0, 3)
    supported_platforms = ['windows', 'osx', 'linux']

    minimum_calibre_version = (5, 0, 0)

    # Ordered list of supported formats
    FORMATS     = ['epub', 'pdf', 'fb2', 'txt', 'pdf', 'html', 'djvu', 'doc', 'docx', 'rtf', 'chm']

    CAN_SET_METADATA = ['collections']

    # ---------------------------------------------------------------------------
    # PocketBook Devices
    #
    # Device    VENDOR_ID    PRODUCT_ID
    # ---------------------------------
    # PB632     0xfffe       0x0001
    # PB628     ???          ???
    # PB1040    0x18d1       0x0001

    VENDOR_ID   = [0xfffe, 0x18d1]
    PRODUCT_ID  = [0x0001]

    BCD         = [0x0230, 0x101]


    EBOOK_DIR_MAIN = 'Books'
    SCAN_FROM_ROOT = True
    SUPPORTS_SUB_DIRS = True

    VENDOR_NAME = ['USB_2.0']
    WINDOWS_MAIN_MEM = WINDOWS_CARD_A_MEM = ['USB_FLASH_DRIVER']


    def open(self, connected_device, library_uuid):
        super().open(connected_device, library_uuid)
        
        debug_print('PB_IMPROVED: open()')

        # get the lookup name of the read column from the settings
        self.read_lookup_name = self.settings().extra_customization[self.OPT_READ_LOOKUP_NAME]
        debug_print('PB_IMPROVED: read lookup name: ' + self.read_lookup_name)

        # get the path of the device database file
        self.dbpath = self._getexplorerdb(self._main_prefix)
        debug_print('PB_IMPROVED: Found database at path ' + self.dbpath)

        self._cleanup_database()




    # get the path for the sqlite db on the device ('explorer-2.db' or 'explorer-3.db')
    def _getexplorerdb(self, root):
        for version in (3, 2):
            explorer = 'explorer-%i' % version
            dbpath = os.path.join(root, 'system', explorer, explorer + '.db')
            if os.path.exists(dbpath):
                return dbpath
        return


    # cleanup the database on the device
    def _cleanup_database(self):
        debug_print('PB_IMPROVED: database cleanup')

        with closing(sqlite.connect(self.dbpath)) as connection:

            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    DELETE FROM BOOKS_SETTINGS
                    WHERE BOOKID IN
                    (
                        SELECT ID
                        FROM BOOKS_IMPL
                        WHERE ID NOT IN
                        (
                            SELECT BOOK_ID
                            FROM FILES
                        )
                    )
                ''')
                rows_affected = cursor.rowcount
                debug_print('PB_IMPROVED: %d rows from books_settings deleted' %(rows_affected))

            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    DELETE FROM BOOKTOGENRE
                    WHERE BOOKID IN
                    (
                        SELECT ID
                        FROM BOOKS_IMPL
                        WHERE ID NOT IN
                        (
                            SELECT BOOK_ID
                            FROM FILES
                        )
                    )
                ''')
                rows_affected = cursor.rowcount
                debug_print('PB_IMPROVED: %d rows from booktogenre deleted' %(rows_affected))

            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    DELETE FROM SOCIAL
                    WHERE BOOKID IN
                    (
                        SELECT ID
                        FROM BOOKS_IMPL
                        WHERE ID NOT IN
                        (
                            SELECT BOOK_ID
                            FROM FILES
                        )
                    )
                ''')
                rows_affected = cursor.rowcount
                debug_print('PB_IMPROVED: %d rows from social deleted' %(rows_affected))

            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    DELETE FROM BOOKS_IMPL
                    WHERE ID NOT IN
                    (
                        SELECT BOOK_ID
                        FROM FILES
                    )
                ''')
                rows_affected = cursor.rowcount
                debug_print('PB_IMPROVED: %d rows from books_impl deleted' %(rows_affected))

            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    DELETE FROM BOOKS_FAST_HASHES
                    WHERE BOOK_ID NOT IN
                    (
                        SELECT BOOK_ID
                        FROM FILES
                    )
                ''')
                rows_affected = cursor.rowcount
                debug_print('PB_IMPROVED: %d rows from books_fast_hashes deleted' %(rows_affected))


            connection.commit()


    # update metadata
    def synchronize_with_db(self, db, book_id, book_metadata, first_call):

        changed_books = set()

        if first_call:
            debug_print('PB_IMPROVED: start sychronize_with_db')
        
            # check if the read column exists in Calibre
            fm = db.field_metadata.custom_field_metadata()

            read_column = fm[self.read_lookup_name]
            self.has_read_column = read_column != None and read_column['datatype'] == 'bool'

            debug_print('PB_IMPROVED: read-column: ' + self.read_lookup_name)


        with closing(sqlite.connect(self.dbpath)) as connection:

            # folder and filename on the device
            path = book_metadata.path.replace(self._main_prefix, '')
            folder = os.path.dirname(path)
            filename = os.path.basename(path)

            # Normalize path delimiter for Windows devices
            folder = folder.replace('\\', '/')

            # get the book_id of the book in the device database
            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    SELECT f.BOOK_ID
                    FROM FILES f
                    JOIN FOLDERS fld ON fld.ID = f.FOLDER_ID 
                    WHERE f.FILENAME = ?
                    AND fld.NAME LIKE ?
                ''', (filename, '%' + folder))
                row = cursor.fetchone()

            if row == None:
                debug_print('PB_IMPROVED: Book not found on device: ' + ', '.join(book_metadata.authors) + ': ' + book_metadata.title)
                debug_print('PB_IMPROVED: ', folder)
                debug_print('PB_IMPROVED: ', filename)

            else:
                device_book_id = row[0]

                # The PocketBook does not handle metadata of pdf files correctly,
                # so check if we need to correct author and title
                with closing(connection.cursor()) as cursor:
                    cursor.execute('''
                        SELECT TITLE
                             , AUTHOR
                             , FIRSTAUTHOR
                             , SORT_TITLE
                        FROM BOOKS_IMPL
                        WHERE ID = ?
                    ''', (device_book_id,))
                    row = cursor.fetchone()

                if row != None:
                    title,author,firstauthor,sort_title = row

                    if (title != book_metadata.title or 
                        author != book_metadata.authors[0] or
                        sort_title != book_metadata.title_sort or
                        firstauthor != book_metadata.authors[0]):
                        debug_print('PB_IMPROVED: Title or author mismatch')
                        debug_print('PB_IMPROVED: ', book_metadata.title, title)
                        debug_print('PB_IMPROVED: ', book_metadata.title_sort, sort_title)
                        debug_print('PB_IMPROVED: ', str(book_metadata.authors))
                        debug_print('PB_IMPROVED: ', str(book_metadata.author_sort))

                        with closing(connection.cursor()) as update_cursor:
                            update_cursor.execute('''
                                UPDATE BOOKS_IMPL
                                SET TITLE = ?
                                    , FIRST_TITLE_LETTER = ?
                                    , AUTHOR = ?
                                    , FIRSTAUTHOR = ?
                                    , FIRST_AUTHOR_LETTER = ?
                                    , SORT_TITLE = ?
                                WHERE ID = ?
                            ''', (
                                book_metadata.title,
                                book_metadata.title[:1].upper(),
                                book_metadata.authors[0],
                                book_metadata.authors[0],
                                book_metadata.authors[0][:1].upper(),
                                book_metadata.title_sort,
                                device_book_id
                            ))

                        connection.commit()


                if not self.has_read_column:
                    return (None, (None, False))

                # get the value of the read column from Calibre
                calibre_read = bool(db.new_api.field_for(self.read_lookup_name, book_id))

                # get the completed status for this book from the device
                with closing(connection.cursor()) as cursor:
                    cursor.execute('''
                        SELECT COMPLETED
                        FROM BOOKS_SETTINGS
                        WHERE BOOKID = ?
                        AND PROFILEID = 1
                    ''', (device_book_id,))
                    row = cursor.fetchone()

                if row == None:
                    has_book_settings = False
                    device_read = False
                else:
                    has_book_settings = True
                    device_read = bool(row[0])
                

                if (calibre_read or device_read) and calibre_read != device_read:
                    debug_print('PB_IMPROVED: --------------')
                    debug_print('PB_IMPROVED: ' + str(book_metadata.authors))
                    debug_print('PB_IMPROVED: ' + book_metadata.title)
                    debug_print('PB_IMPROVED: Device book id: ' + str(device_book_id))            
                    debug_print('PB_IMPROVED: Calibre read: ' + str(calibre_read))
                    debug_print('PB_IMPROVED: Device read: ' + str(device_read))

                    if not calibre_read:
                        # book is marked read on the device, but not in Calibre
                        debug_print('PB_IMPROVED: Update Calibre database for book_id: ' + str(book_id))
                        changed_books |= db.new_api.set_field(self.read_lookup_name, {book_id: True})
                    else:
                        # book is marked read in Calibre, but not on device
                        debug_print('PB_IMPROVED: Update device database')

                        with closing(connection.cursor()) as cursor:
                            if not has_book_settings:
                                debug_print('PB_IMPROVED: Create new settings entry')
                                cursor.execute('''
                                    INSERT INTO BOOKS_SETTINGS
                                    (
                                        BOOKID,
                                        PROFILEID,
                                        COMPLETED,
                                        COMPLETED_TS
                                    )
                                    VALUES
                                    (
                                        ?,
                                        1,
                                        1,
                                        ?
                                    )
                                ''',(device_book_id, int(time.time())))
                            else:
                                debug_print('PB_IMPROVED: Update settings entry')
                                cursor.execute('''
                                    UPDATE BOOKS_SETTINGS
                                    SET COMPLETED = 1
                                    , COMPLETED_TS = ?
                                    WHERE BOOKID = ?
                                ''', (int(time.time()),device_book_id))
                        
                        connection.commit()
            

        if changed_books:
            return (changed_books, (None, False))

        return (None, (None, False))


    # delete books
    def delete_books(self, paths, end_session=True):
        debug_print('PB_IMPROVED: delete_books()')

        with closing(sqlite.connect(self.dbpath)) as connection:
            for i, path in enumerate(paths):
                path = path.replace(self._main_prefix, '')
                debug_print('PB_IMPROVED: ' + path)

                folder = os.path.dirname(path)
                filename = os.path.basename(path)

                with closing(connection.cursor()) as cursor:
                    cursor.execute('''
                        SELECT f.ID
                             , f.FOLDER_ID
                             , f.BOOK_ID
                        FROM FILES f
                        JOIN FOLDERS fld ON fld.ID = f.FOLDER_ID 
                        WHERE f.FILENAME = ?
                        AND fld.NAME LIKE ?
                    ''', (filename, '%' + folder))
                    row = cursor.fetchone()

                if row != None:
                    # book_id found, delete all database entries
                    file_id,folder_id,book_id = row
                    debug_print('PB_IMPROVED: file_id: ' + str(file_id) + ', folder_id: ' + str(folder_id) + ', book_id: ' + str(book_id))

                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM SOCIAL
                            WHERE BOOKID = ?
                        ''', (book_id,))

                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM BOOKS_SETTINGS
                            WHERE BOOKID = ?
                        ''', (book_id,))

                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM FILES
                            WHERE ID = ?
                        ''', (file_id,))

                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM BOOKS_FAST_HASHES
                            WHERE BOOK_ID = ?
                        ''', (book_id,))

                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM FOLDERS
                            WHERE ID = ?
                            AND ID NOT IN (
                                SELECT FOLDER_ID 
                                FROM FILES 
                            )
                        ''', (folder_id,))

                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM BOOKS_IMPL
                            WHERE ID = ?
                        ''', (book_id,))

                else:
                    debug_print('PB_IMPROVED: Book not found in database')

                    folder = os.path.dirname(path)
                    with closing(connection.cursor()) as cursor:
                        cursor.execute('''
                            DELETE FROM FOLDERS
                            WHERE NAME LIKE ?
                            AND ID NOT IN (
                                SELECT FOLDER_ID 
                                FROM FILES 
                            )
                        ''', ('%' + folder,))
                        rows_affected = cursor.rowcount
                        debug_print('PB_IMPROVED: %d folder(s) deleted' %(rows_affected))

            connection.commit()


        super().delete_books(paths, end_session)
