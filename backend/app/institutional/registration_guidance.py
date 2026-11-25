"""Editorial help from the public forms reviewed on 2026-11-24; no form submission."""

import re
import unicodedata


def relevant(question):
    text = "".join(c for c in unicodedata.normalize("NFD", question or "") if not unicodedata.combining(c)).lower()
    return bool(re.search(
        r"inscri|formulario|diligenc|llenar|llen[eo]|anex|documento|acudiente|"
        r"campo|archivo|adjunt|registro|matricul|grupo|municipio|departamento|colegio|"
        r"correo|cedula|identidad|sanguin|fotograf|acudi|grado|politica de datos|"
        r"no me (?:deja|sale|carga)|no puedo (?:continuar|enviar)|"
        r"\b(?:eps|sisben|rh|jpg|pdf|png)\b", text
    ))


FACTS = [
    {
        "topic": "inscripcion_ayuda_general",
        "source": "https://siieplus.online/SIIEWebPlus/inscripciones",
        "reviewed_at": "2026-11-24",
        "text": (
            "GUÍA DEL FORMULARIO GENERAL CBN (incluye Gastronomía e Inglés), revisada el 24/11/2026. "
            "Tiene once secciones desplegables: Datos Personales, Datos Generales, Estudios Secundarios, "
            "Formación Complementaria, Información Laboral, Referencias Familiares, Familia CBN, "
            "Información Socioeconómica, Grupos Especiales, Padres y Anexo de documentos. "
            "Primero elegir Programa y jornada; al cambiar programa la página se actualiza y puede cerrar secciones. "
            "En Inglés el selector dice PROEFICIENCIA EN INGLES, diurna o nocturna. Cocina Nacional e Internacional "
            "tiene diurna/nocturna; Repostería y Pastelería, diurna/fines de semana. BARISMO y BARTENDER aparecen "
            "como opciones separadas: si desea la formación conjunta, confirmar con Admisiones cuál seleccionar; "
            "no pedir dos inscripciones ni dos pagos ni contradecir la ficha de formación conjunta. "
            "Datos Personales pide tipo/número de documento, ciudad de expedición, apellidos, nombres, fecha y lugar "
            "de nacimiento. Datos Generales pide residencia, dirección, teléfonos, correo, estado civil, estrato, "
            "género y grupo sanguíneo/RH. Acudiente para menores; para adultos la página indica contacto de emergencia. "
            "Estudios Secundarios pide grado, institución, título, graduación, modalidad y municipio. Las demás "
            "secciones recogen estudios complementarios, empleo, una referencia familiar distinta al acudiente "
            "que no viva en la misma dirección, vínculos con CBN, financiación, salud, grupos especiales y padres. "
            "Responder con datos reales; no inventar datos ni recomendar respuestas falsas para superar campos. "
            "Anexo de documentos cambia al elegir programa. La página indica imágenes .jpg y fotografía reciente "
            "4x4; su aviso destaca foto, diploma y documento de identidad. Inglés mostró además acta de grado, "
            "EPS/SISBEN e identificación del acudiente para menores. Cocina, Barismo, Bartender y Repostería "
            "mostraron anexos adicionales de salud; Barismo/Bartender/Repostería también Carta de Compromiso; "
            "Cocina/Repostería mostraron certificado Mi Vacuna. Son campos observados, no una nueva declaración "
            "de obligatoriedad o vigencia de cada examen: ante diferencia con la ficha actual consultar Admisiones. "
            "No trasladar a este formulario los límites de archivos de PRE-ICFES, pues aquí no se verificaron. "
            "Al final la persona revisa la política de tratamiento de datos y decide aceptarla antes de Enviar."
        ),
    },
    {
        "topic": "inscripcion_ayuda_preicfes",
        "source": "https://siieplus.online/SIIEWEBPLUS/PreIcfes/Inscripcion.html",
        "reviewed_at": "2026-11-24",
        "text": (
            "GUÍA EXCLUSIVA PRE-ICFES, revisada el 24/11/2026. Tres pasos con botones Continuar, Atrás y "
            "navegación por el número del paso. 1 Datos personales: tipo/número de documento, nombres, primer "
            "apellido, fecha de nacimiento, género, grupo sanguíneo, RH, celular y correo; segundo apellido "
            "está marcado opcional. Escribir los datos como en el documento. 2 Residencia y colegio: elegir "
            "Departamento escribiendo y seleccionando la opción de la lista; así se habilita Ciudad o municipio. "
            "Escribir la ciudad y seleccionar la coincidencia, no sólo dejar texto escrito. Luego dirección, "
            "colegio y grado actual o Egresado. 3 Grupo y documentos: Grupo A/PRE ICFES SABADO, sábados 7am–12m; "
            "Grupo B/PRE ICFES SABADO B, sábados 1pm–6pm; Grupo C/PRE ICFES DOMINGO, domingos 7am–12m. "
            "Corresponden por horario a G1, G2 y G3 del afiche; no prometer cupo por ver una opción. "
            "Elegir grupo muestra los anexos. En A/B/C se observó DOCUMENTO DE IDENTIDAD del aspirante, "
            "fotocopia ampliada al 150%; acepta PDF, JPG o PNG, máximo 10MB por archivo y 50MB en total. "
            "Seleccionar archivo o arrastrarlo en la zona indicada; revisar lo que muestre el grupo vigente. "
            "Los campos con * son obligatorios. La persona revisa la política y decide marcar Acepto la política "
            "de tratamiento de datos antes de Confirmar inscripción. No aplicar aquí el mínimo de 16 años "
            "de los otros programas. La navegación entre pasos se observó sin enviar datos; no confirma validación "
            "final, inscripción, pago ni acceso automático a la plataforma."
        ),
    },
    {
        "topic": "inscripcion_ayuda_y_proteccion",
        "source": "owner_reviewed:2026-11-24:registration-help",
        "reviewed_at": "2026-11-24",
        "text": (
            "AYUDA DE INSCRIPCIÓN: orientar sólo el paso o campo que la persona pregunta, en mensajes breves; "
            "no volcar toda la guía. Si el contexto no identifica formulario/programa, aclararlo una vez. "
            "No pedir números completos de documento, fotos, exámenes, historia clínica, datos de familiares "
            "ni claves por el chat: la persona los diligencia o adjunta directamente en el formulario oficial. "
            "Si hay error, preguntar el paso/campo y aviso exacto sin datos personales, o una captura recortada "
            "y ocultando datos. Verificar selección real de opciones, campos señalados, correo y formato/tamaño "
            "de archivo según ese formulario. No inventar mensajes de error, constancias, códigos de inscripción "
            "ni límites no observados. No aconsejar omitir documentos obligatorios o falsear datos. Si un campo "
            "no aplica, no hay el programa/jornada o hay requisitos contradictorios, consultar Admisiones sin "
            "prometer exención. La persona decide grupo, consentimiento y envío; no aceptar la política ni "
            "enviar por ella. Si no aparece confirmación tras enviar, no afirmar éxito ni pedir envíos repetidos: "
            "revisar el aviso y confirmar con Admisiones. Un enlace abierto o una captura de formulario "
            "no prueba inscripción completada ni pago. Guía fechada; la pantalla actual puede cambiar."
        ),
    },
]
