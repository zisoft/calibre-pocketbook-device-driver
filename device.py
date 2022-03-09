__license__   = 'GPL v3'
__copyright__ = '2022 Mario Zimmermann <mail@zisoft.de>'
__docformat__ = 'restructuredtext en'

'''
PocketBook 632 Driver.
'''

import os, time, json, shutil
import sqlite3 as sqlite
from contextlib import closing
import calibre
import traceback
from itertools import cycle


from calibre.devices.usbms.driver import USBMS, debug_print
from calibre.devices.usbms.books import BookList, Book
from calibre.ebooks.metadata.book.json_codec import JsonCodec


class POCKETBOOK632(USBMS):

    '''
    Class for PocketBook 632 drivers. Implements the logic for 
    managing the read status of books and several other improvements.

    This is a two-way sync, no matter where you mark a book as read (on the 
    device or in Calibre), the read status is synchronized on both platforms.
   '''

    name  = 'PocketBook632'
    gui_name = 'PocketBook 632'
    description    = _('Communicate with PocketBook 632 readers')
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


    def open(self, connected_device, library_uuid):
        super().open(connected_device, library_uuid)
        
        debug_print('POCKETBOOK632: open()')

        self.dbpath = self._getexplorerdb(self._main_prefix)
        debug_print('POCKETBOOK632: Found database at path ' + self.dbpath)

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
        debug_print('POCKETBOOK632: database cleanup')

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
                debug_print('POCKETBOOK632: %d rows from books_settings deleted' %(rows_affected))

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
                debug_print('POCKETBOOK632: %d rows from booktogenre deleted' %(rows_affected))

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
                debug_print('POCKETBOOK632: %d rows from social deleted' %(rows_affected))

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
                debug_print('POCKETBOOK632: %d rows from books_impl deleted' %(rows_affected))

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
                debug_print('POCKETBOOK632: %d rows from books_fast_hashes deleted' %(rows_affected))


            connection.commit()


    # update metadata
    def synchronize_with_db(self, db, book_id, book_metadata, first_call):

        # TODO: check if the #read column exists in calibre

        changed_books = set()

        if first_call:
            debug_print('POCKETBOOK632: start sychronize_with_db')


        with closing(sqlite.connect(self.dbpath)) as connection:

            # get the value of the #read column
            calibre_read = bool(db.new_api.field_for('#read', book_id))

            # get the book_id of the device database
            with closing(connection.cursor()) as cursor:
                cursor.execute('''
                    SELECT ID
                    FROM BOOKS_IMPL
                    WHERE AUTHOR = ?
                    AND TITLE = ?
                ''', (', '.join(book_metadata.authors), book_metadata.title))
                row = cursor.fetchone()

            if row == None:
                debug_print('POCKETBOOK632: Book not found on device: ' + ', '.join(book_metadata.authors) + ': ' + book_metadata.title)
            else:
                device_book_id = row[0]

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
                    debug_print('POCKETBOOK632: --------------')
                    debug_print('POCKETBOOK632: ' + str(book_metadata.authors))
                    debug_print('POCKETBOOK632: ' + book_metadata.title)
                    debug_print('POCKETBOOK632: Device book id: ' + str(device_book_id))            
                    debug_print('POCKETBOOK632: Calibre read: ' + str(calibre_read))
                    debug_print('POCKETBOOK632: Device read: ' + str(device_read))

                    if not calibre_read:
                        # book is marked read on the device, but not in calibre
                        debug_print('POCKETBOOK632: Update calibre database for book_id: ' + str(book_id))
                        changed_books |= db.new_api.set_field('#read', {book_id: True})
                    else:
                        # book is marked read in calibre, but not on device
                        debug_print('POCKETBOOK632: Update device database')

                        with closing(connection.cursor()) as cursor:
                            if not has_book_settings:
                                debug_print('POCKETBOOK632: Create new settings entry')
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
                                debug_print('POCKETBOOK632: Update settings entry')
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
        debug_print('POCKETBOOK632: delete_books()')

        with closing(sqlite.connect(self.dbpath)) as connection:
            for i, path in enumerate(paths):
                path = path.replace(self._main_prefix, '')
                debug_print('POCKETBOOK632: ' + path)
                folder = os.path.dirname(path)
                filename = os.path.basename(path)
                debug_print('POCKETBOOK632: ' + filename)

                with closing(connection.cursor()) as cursor:
                    cursor.execute('''
                        SELECT ID
                             , FOLDER_ID
                             , BOOK_ID
                        FROM FILES
                        WHERE FILENAME = ?
                    ''', (filename,))
                    row = cursor.fetchone()

                    if row != None:
                        # book_id found, delete all database entries
                        file_id,folder_id,book_id = row
                        debug_print('POCKETBOOK632: file_id: ' + str(file_id) + ', folder_id: ' + str(folder_id) + ', book_id: ' + str(book_id))

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
                        debug_print('POCKETBOOK632: Book not found in database')

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
                            debug_print('POCKETBOOK632: %d folder(s) deleted' %(rows_affected))

                    connection.commit()


        super().delete_books(paths, end_session)

