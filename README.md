# Calibre Device Driver For PocketBook Devices

This is an improved device driver for PocketBook devices. I have developed it
for my _PocketBook Touch HD 3_ but it will probably work with other PocketBook devices
as well.


## Improvements

### Read Status
The PocketBook supports to mark a book as read. To synchronize this status with Calibre, create a user defined column of type Yes/No and with the lookup name `#read`. This is a two-way sync, no matter where you mark a book as read (on the device or in Calibre), the read status is synchronized on both platforms.

### Database Cleanup
With a universal USBMS driver, the corresponding database entries on the device are not deleted when you delete a book on the device from within Calibre, leaving hundreds of abandoned database entries over time. Of course, theses entries doesn't hurt, but to keep the database in a clean and consistent state, a database cleanup is performed on every device connect.

### Book Deletion
With this device driver the corresponding database entries are also removed when you delete a book from within Calibre.


## Installation
Download the `pocketbook-632.zip` file. Open Calibre, go to _Preferences, Advanced, Plugins_ and choose _Load Plugin from file_. Choose the `pocketbook-632.zip` file.