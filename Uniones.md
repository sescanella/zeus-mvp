Para la version 4.0 de la app vamos a incluir las uniones.
Cada spool esta conformado por uniones
Las uniones son armadas y soldadas
Un spool puede tener entre 0 a 20 uniones.
Las unidad de medida de las uniones es su pulgada
Las uniones pueden ser clasificadas por tipo, existen 4 tipos: BW, SO, FILL y BR.
Cada union tiene una fecha de inicio y una fecha de termino
Cada union es realizada por un trbaajdor en particular, el cual la inicia y termina, este proceso no puede ser compartido por trabajdores y no puede ser interrumpido.
Cada union es sometida a pruebas de calidad, estas pruebas pueden ser: PT, MT, RT, UT o NA. NA significa que no aplican las pruebas. el resto de siglas son efectivamente pruebas. Una union puede estar sometida a una sola prueba o a ninguna, ademas cada prubea puede ser aprobada o rechazada.
Cada union tiene su respectivo numero de union, este numero de union es secuancial y por spool. por ejemplo si un spool esta conformado por 3 uniones. eso sifnifica que existe la union 1, la union 2 y la union 3. este numero de union no se puede repetir por spool.
En el gsheets existe una hoja llamada: Uniones
Las columnas de la hoja uniones son: ID (Un concat de OT+N_UNION), OT (Esta es la columna es compartida en la hoja Operaciones por lo que es nuetra key para interceptar rows entre ambas hojas), N_UNION (esta columna muestra el numero secuancial de la union del spool este valor puede ser de 0 a 20 y no se puede repetir entre mismos OT), DN_UNION (En esta columna va la unidad de media de pulgadas de la union), TIPO_UNION (existen 4 valores posibles: BW, SO, FILL o BR), ARM_FECHA_INICIO (inicio del armado de la union), ARM_FECHA_FIN (fin del armado de la union), ARM_WORKER (esoecifica el trabajdor que realizo el armado de esa union), SOL_FECHA_INICIO, SOL_FECHA_FIN, SOL_WORKER (Estas 3 columnas SOL_ utilizan la misma logica que las columnas ARM, pero para el soldado de cada union), NDT_UNION (Especifica el tipo de prueba a la que fue sometida la union: NA, UT, RT, PT o MT), R_NDT_UNION (Es el resultado de la prueba la cual puede ser Aprobado o Rechazado).
El formato de las columnas FECHA es DD-MM-AAAA-hh-mm
El formato de las columnas WORKER es XY(id) Siendo X la iniciar del nombre en mayuscula, Y la inicial del apellido en Mayuscula.