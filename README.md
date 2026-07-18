# LisCore

uvicorn app.main:app --reload


# crear network para minio 
docker network create clinizad_network


^XA
^LH0,0
^FO45,20^AB,20,1^FD{patient_full_name}^FS
^FO45,45^AB,10,1^FDIDENTIFICACION:{identification}^FS
^FO45,60^AB,10,1^FDEMPRESA:{enterprise_name}^FS
^FO260,60^AB,10,1^FDEDAD:{age_str}^FS

^BY2,3,150
^FO25,80^BCN,80,N,Y,N^FD{barcode_value}^FS

^FO370,40^ADB,25,1^FD{label_number}^FS
^FO5,80^ABB,15,1^FD{work_}^FS

^FO45,165^AB,18,1^FD{tests_line}^FS
^FO45,189^AB,10,1^FD TM-{sample_type_name}^FS

^PQ1
^XZ