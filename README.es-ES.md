

# Controlador de dispositivo Calibre para dispositivos PocketBook

Este es un controlador de dispositivo mejorado para dispositivos PocketBook. Lo he desarrollado para mi _PocketBook Touch HD 3_, pero probablemente también funcione con otros dispositivos PocketBook.


## Mejoras

### Estado de lectura
El PocketBook permite marcar un libro como leído. Para sincronizar este estado con Calibre, crea una columna definida por el usuario de tipo Sí/No y establece su nombre en la configuración del controlador.

Se trata de una sincronización bidireccional: sin importar dónde marques un libro como leído (en el dispositivo o en Calibre), el estado de lectura se sincroniza en ambas plataformas.

### Limpieza de la base de datos
Las entradas de base de datos correspondientes en el dispositivo no se eliminan cuando borras un libro en el dispositivo, lo que genera un gran número de entradas de base de datos abandonadas con el tiempo. Por supuesto, estas entradas no causan problemas, pero para mantener la base de datos en un estado limpio y coherente, se realiza una limpieza de la base de datos cada vez que se conecta el dispositivo.

### Eliminación de libros
Al eliminar un libro en el dispositivo, no se eliminan todas las entradas de base de datos correspondientes. Volver a subir el mismo libro provoca que el libro no se muestre en la biblioteca, lo que imposibilita volver a abrirlo.

Esto se soluciona con este controlador de dispositivo: eliminar un libro en el dispositivo desde Calibre limpia la base de datos.

### Metadatos de los archivos PDF
El PocketBook no gestiona correctamente los metadatos de los archivos PDF; principalmente, los campos de título y autor se desconfiguran. Este controlador de dispositivo limpia los campos de metadatos cada vez que se conecta el dispositivo.

## Instalación
Descarga el `pocketbook632.zip` file. Abre Calibre, ve a _Preferencias, Avanzado, Complementos_ y selecciona _Cargar complemento desde archivo_. Elige el archivo `pocketbook632.zip`. Reinicia Calibre.

### Configurar el complemento
Establece el nombre de tu columna personalizada de tipo Sí/No en el cuadro de configuración del complemento (el valor predeterminado es `#read`)
