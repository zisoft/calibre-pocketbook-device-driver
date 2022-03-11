# Calibre Device Driver For PocketBook Devices

This is an improved device driver for PocketBook devices. I have developed it
for my _PocketBook Touch HD 3_ but it will probably work with other PocketBook devices
as well.


## Improvements

### Read Status
The PocketBook supports to mark a book as read. To synchronize this status with Calibre, create a user defined column of type Yes/No and set its lookup name in the driver settings.

This is a two-way sync, no matter where you mark a book as read (on the device or in Calibre), the read status is synchronized on both platforms.

### Database Cleanup
The corresponding database entries on the device are not deleted when you delete a book on the device, leaving lots of abandoned database entries over time. Of course, theses entries doesn't hurt, but to keep the database in a clean and consistent state, a database cleanup is performed on every device connect.

### Book Deletion
When deleting a book on the device not all of the corresponding database entries are deleted. Uploading the same book again leads to the effect that the book is not displayed in the library, making it impossible to open it again.

This is fixed in this device driver, deleting a book on the device from Calibre cleans up the database.

### Metadata of PDF files
The PocketBook does not handle the metadata of PDF files correctly, mainly the title and author fields are messed up. This device driver cleans the metadata fields on device connect.

## Installation
Download the `pocketbook632.zip` file. Open Calibre, go to _Preferences, Advanced, Plugins_ and choose _Load Plugin from file_. Choose the `pocketbook632.zip` file. Restart Calibre.

### Configure the Plugin
Set the lookup name of your custom Yes/No column in the plugin's configuration dialog (default is `#read`) 
