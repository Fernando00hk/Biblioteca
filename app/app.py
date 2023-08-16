import os
from io import BytesIO
import traceback
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    Blueprint,
    login_required,
    logout_user,
    current_user,
)
from flask_paginate import Pagination, get_page_parameter
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    flash,
    send_file,
    make_response,
    session,
)
from flask_login import login_user, current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from flask import Flask, render_template, request
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request
import secrets
from flask_mail import Mail, Message
import datetime

Custom_tags = Blueprint("custom_tags", __name__)
app = Flask(__name__)
csrf = CSRFProtect()
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "alan"
app.config["MYSQL_PASSWORD"] = "password"
app.config["MYSQL_DB"] = "biblioteca"
app.secret_key = "mysecretkey"
app.config["UPLOAD_FOLDER"] = "static/imagenes/imglibros"
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = "jcoronacruz4@gmail.com"
app.config["MAIL_PASSWORD"] = "ustyzqtoitspgmns"
app.config["MAIL_DEFAULT_SENDER"] = "jcoronacruz4@gmail.com"

mysql = MySQL(app)
CARPETA_IMAGENES = os.path.join(app.root_path, "static", "imagenes", "imglr")
CARPETA_IMAGENES = os.path.join(app.root_path, "static", "imagenes", "imgus")
login_manager = LoginManager(app)
mail = Mail(app)


class User(UserMixin):
    def __init__(self, user_id, username, email, password):
        self.id = user_id
        self.username = username
        self.email = email
        self.password = password


users_db = {}
tokens_db = {}


@app.route("/confirm/<token>", methods=["GET"])
def confirm_email(token):
    # Conectar a la base de datos
    cur = mysql.connection.cursor()

    # Verificar si el token es válido
    cur.execute("SELECT id FROM users WHERE confirmation_token = %s", (token,))
    user_id = cur.fetchone()

    if user_id:
        # Actualizar el estado de confirmación del correo electrónico
        cur.execute("UPDATE users SET email_confirmed = 1 WHERE id = %s", (user_id[0],))
        mysql.connection.commit()
        cur.close()

        return "Correo electrónico confirmado. ¡Puedes acceder a tu cuenta!"
    else:
        cur.close()
        return "Token inválido."


# Ruta para cerrar sesión
@app.route("/logout")
@login_required
def logout():
    # Cerrar la sesión del usuario
    logout_user()
    session.clear()  # Limpiar toda la información de la sesión
    # Redirigir a la página de inicio de sesión
    return redirect(url_for("login"))


@app.context_processor
def inject_user():
    return dict(current_user=current_user)


@login_manager.user_loader
def load_user(user_id):
    # Conecta con la base de datos para buscar el usuario por su id
    # Implementa la lógica para realizar la consulta SQL y obtener el usuario
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()

    if user_data:
        # Si se encontró el usuario en la base de datos, crea una instancia de la clase User
        user = User(
            user_id=user_data[0],
            username=user_data[1],
            email=user_data[2],
            password=user_data[3],
        )
        return user
    else:
        # Si no se encontró el usuario, devuelve None
        return None


@app.route("/")
def index():
    data = {
        "titulo": "users",
    }
    return render_template("index.html", current_user=current_user, data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Verificar las credenciales en la base de datos
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        account = cur.fetchone()
        cur.close()

        if account and check_password_hash(account[3], password):
            if account[6] == 0:  # Verificar si el correo electrónico no está confirmado
                flash(
                    "Debes confirmar tu correo electrónico antes de iniciar sesión.",
                    "error",
                )
            else:
                session["logueado"] = True
                session["id"] = account[0]
                session["id_rol"] = account[4]

                # Crear instancia del objeto User para iniciar sesión
                user = User(
                    user_id=account[0],
                    username=account[1],
                    email=account[2],
                    password=account[3],
                )
                login_user(user)

                if session["id_rol"] == 1 or session["id_rol"] == 2:
                    return redirect(url_for("index"))
        else:
            flash("Credenciales incorrectas. Por favor, inténtalo de nuevo.", "error")

    return render_template("login.html")


# Ruta para la página de registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Obtener los datos del formulario de registro
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        fecha_nacimiento = request.form["fecha_nacimiento"]
        genero = request.form["genero"]
        curp = request.form["curp"]

        # Generar un token de confirmación
        token = generate_confirmation_token()

        # Guardar el usuario y el token en la base de datos
        save_user_with_token(
            username, email, hashed_password, token, fecha_nacimiento, genero, curp
        )

        # Enviar correo de confirmación
        send_confirmation_email(email, token)

        flash(
            "Se ha enviado un correo de confirmación. Por favor, verifica tu correo electrónico."
        )
        return redirect("/login")

    return render_template("register.html")


# Función para generar un token de confirmación (debes implementarla)
def generate_confirmation_token():
    return secrets.token_urlsafe(32)


# Función para guardar el usuario y el token en la base de datos (debes implementarla)
def save_user_with_token(
    username, email, hashed_password, token, fecha_nacimiento, genero, curp
):
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password, id_rol, confirmation_token, fecha_nacimiento, genero, curp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            username,
            email,
            hashed_password,
            2,
            token,
            fecha_nacimiento,
            genero,
            curp,
        ),  # Asignar id_rol con valor 2 por defecto
    )
    mysql.connection.commit()
    cur.close()


# Función para enviar el correo de confirmación
def send_confirmation_email(email, token):
    subject = "Confirma tu correo electrónico"
    sender = app.config["MAIL_USERNAME"]
    recipients = [email]

    # Crea el contenido del correo
    message_body = f"Hola,\n\nPor favor, confirma tu correo electrónico haciendo clic en el siguiente enlace:\n\n{url_for('confirm_email', token=token, _external=True)}\n\nGracias,\nTu App"

    # Crea el mensaje
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = message_body

    # Envía el correo
    mail.send(msg)


@app.route("/libro/agregar", methods=["GET", "POST"])
def libro_agregar():
    if request.method == "POST":
        titulo = request.form["titulo"]
        autor = request.form["autor"]
        codigo_barras = request.form["codigo_barras"]
        imagen = request.files["imagen"] if "imagen" in request.files else None
        categoria = request.form["categoria"]
        sinopsis = request.form["sinopsis"]
        piezas = request.form["piezas"]
        fecha_publicacion = request.form["fecha_publicacion"]

        # Guardar el nombre de la imagen en la base de datos
        nombre_imagen = None  # Por defecto, no hay imagen

        if imagen:
            # Obtener el nombre del archivo de imagen
            nombre_imagen = secure_filename(imagen.filename)

            # Guardar la imagen en el sistema de archivos
            directorio_imagenes = "static/imagenes/imglibros"
            if not os.path.exists(directorio_imagenes):
                os.makedirs(directorio_imagenes)

            ruta_imagen = os.path.join(directorio_imagenes, nombre_imagen)
            imagen.save(ruta_imagen)

        # Insertar el nuevo libro en la base de datos
        cur = mysql.connection.cursor()
        sql = "INSERT INTO libros (titulo, autor, codigo_barras, imagen, categoria, sinopsis, piezas, fecha_publicacion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        valores = (
            titulo,
            autor,
            codigo_barras,
            nombre_imagen,
            categoria,
            sinopsis,
            piezas,
            fecha_publicacion,
        )
        cur.execute(sql, valores)
        mysql.connection.commit()
        cur.close()

        flash("Libro agregado exitosamente!")

        return redirect("/libros")

    return render_template("libro_agregar.html")


PER_PAGE = 2


def libros_Paginar(page):
    cur = mysql.connection.cursor()

    # Ejemplo de consulta paginada (ajusta esto según la estructura de tu tabla)
    offset = (page - 1) * PER_PAGE
    sql = "SELECT * FROM libros LIMIT %s OFFSET %s"
    cur.execute(sql, (PER_PAGE, offset))

    # Obtenemos los resultados y los almacenamos en una lista
    resultados_pagina_actual = cur.fetchall()

    # Consulta para obtener el total de resultados (sin paginación)
    sql_total = "SELECT COUNT(*) FROM libros"
    cur.execute(sql_total)
    total_results = cur.fetchone()[0]

    cur.close()

    return resultados_pagina_actual, total_results


# Read (Ver libros)
@app.route("/libros", methods=["GET"])
def libros():
    buscar = request.args.get("buscar")
    cur = mysql.connection.cursor()

    if buscar:
        # Realizar la búsqueda de libros que coincidan con el término
        sql = "SELECT * FROM libros WHERE titulo LIKE %s OR autor LIKE %s OR codigo_barras LIKE %s"
        valores = (f"%{buscar}%", f"%{buscar}%", f"%{buscar}%")
        cur.execute(sql, valores)
        libros = cur.fetchall()
    else:
        # Obtener todos los libros si no se realizó una búsqueda
        cur.execute("SELECT * FROM libros")
        libros = cur.fetchall()

    cur.close()

    # Obtener la página actual del paginador
    page = request.args.get(get_page_parameter(), type=int, default=1)

    # Función para obtener los resultados de la página actual y el total de resultados
    def libros_Paginar(page, per_page=PER_PAGE):
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        return libros[start_index:end_index], len(libros)

    # Obtener los resultados de la página actual y el total de resultados
    resultados_pagina_actual, total_results = libros_Paginar(page)

    # Generar el objeto de paginación
    pagination = Pagination(
        page=page,
        per_page=PER_PAGE,
        total=total_results,
        outer_window=2,
        inner_window=2,
    )

    return render_template(
        "libros.html", pagination=pagination, libros=resultados_pagina_actual
    )


@app.route("/libro_editar/<int:idlibros>", methods=["GET", "POST"])
def libro_editar(idlibros):
    if request.method == "POST":
        # Obtener otros datos del formulario
        titulo = request.form["titulo"]
        autor = request.form["autor"]
        codigo_barras = request.form["codigo_barras"]

        # Manejar la imagen si se proporciona una nueva
        nueva_imagen = request.files["nueva_imagen"]
        if nueva_imagen and nueva_imagen.filename != "":
            filename = secure_filename(nueva_imagen.filename)
            nueva_imagen.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            # Actualizar la ruta de la imagen en la base de datos
            cur = mysql.connection.cursor()
            sql = "UPDATE libros SET titulo = %s, autor = %s, codigo_barras = %s, imagen = %s WHERE idLibros = %s"
            valores = (titulo, autor, codigo_barras, filename, idlibros)
            cur.execute(sql, valores)
            mysql.connection.commit()

            flash("Libro actualizado exitosamente!")
            return redirect("/libros")

        # Si no se proporcionó una nueva imagen, actualizar otros campos solamente
        cur = mysql.connection.cursor()
        sql = "UPDATE libros SET titulo = %s, autor = %s, codigo_barras = %s WHERE idLibros = %s"
        valores = (titulo, autor, codigo_barras, idlibros)
        cur.execute(sql, valores)
        mysql.connection.commit()

        flash("Libro actualizado exitosamente!")

    # Consultar los datos del libro para renderizar el template
    cur = mysql.connection.cursor()
    sql = "SELECT * FROM libros WHERE idLibros = %s"
    cur.execute(sql, (idlibros,))
    libro = cur.fetchone()
    cur.close()

    if libro is None:
        flash("El libro no existe")
        return redirect("/libros")

    return render_template("editar.html", libro=libro)


@app.route("/libros/ver<int:libro_id>")
def detalle_libro(libro_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM libros WHERE idLibros = %s", (libro_id,))
    libro = cur.fetchone()
    cur.close()

    if libro:
        return render_template("detalle_libro.html", libro=libro)
    else:
        flash("Libro no encontrado.", "danger")
        return redirect("/libros_ver")


# Delete (Borrar libro)
@app.route("/libros/borrar/<int:libro_id>", methods=["GET", "POST"])
def libro_borrar(libro_id):
    if request.method == "POST":
        cur = mysql.connection.cursor()
        sql = "DELETE FROM libros WHERE idLibros = %s"
        cur.execute(sql, (libro_id,))
        mysql.connection.commit()
        cur.close()

        flash("Libro borrado exitosamente!")

    return redirect("/libros")


@app.route("/libros/prestamo/<int:libro_id>", methods=["GET", "POST"])
@login_required
def generar_prestamo(libro_id):
    mensaje_error = ""  # Inicializar el mensaje de error

    if request.method == "POST":
        # Obtener los datos del formulario
        nombre = request.form["nombre"]
        fecha_nacimiento = request.form["fecha_nacimiento"]
        direccion = request.form["direccion"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        institucion = request.form["institucion"]

        # Crear una lista para almacenar los libros seleccionados
        libros = []
        i = 1
        while True:
            autor = request.form.get(f"autor_{i}")
            titulo = request.form.get(f"titulo_{i}")
            codigo = request.form.get(f"codigo_{i}")

            # Verificar si se llenó la información del libro
            if autor and titulo and codigo:
                # Verificar si los datos coinciden con la base de datos
                cur = mysql.connection.cursor()
                cur.execute(
                    "SELECT * FROM libros WHERE Autor = %s AND titulo = %s AND codigo_barras = %s",
                    (autor, titulo, codigo),
                )
                libro_encontrado = cur.fetchone()
                cur.close()

                if libro_encontrado:
                    libros.append({"autor": autor, "titulo": titulo, "codigo": codigo})
                else:
                    flash(
                        f"El libro con Autor: {autor}, Nombre: {titulo}, y Código: {codigo} no coincide en la base de datos.",
                        "danger",
                    )
            else:
                break

            i += 1

        # Obtener la cantidad de piezas solicitadas para cada libro
        for i, libro in enumerate(libros, start=1):
            piezas_solicitadas_str = request.form.get(f"piezas_{i}")

            if piezas_solicitadas_str:
                piezas_solicitadas = int(piezas_solicitadas_str)

                # Obtener la cantidad de piezas disponibles en la base de datos
                cur = mysql.connection.cursor()
                cur.execute(
                    "SELECT piezas FROM libros WHERE Autor = %s AND titulo = %s AND codigo_barras = %s",
                    (libro["autor"], libro["titulo"], libro["codigo"]),
                )
                piezas_disponibles = cur.fetchone()[0]
                cur.close()

                if piezas_solicitadas > piezas_disponibles:
                    mensaje_error = f"No hay suficientes piezas disponibles para el libro {libro['titulo']}."
                    return render_template(
                        "formulario_prestamo.html",
                        libro_id=libro_id,
                        mensaje_error=mensaje_error,
                    )
            else:
                mensaje_error = f"No se proporcionó una cantidad de piezas para el libro {libro['titulo']}."
                return render_template(
                    "formulario_prestamo.html",
                    libro_id=libro_id,
                    mensaje_error=mensaje_error,
                )

        # Resto del código para generar el PDF
        if libros:
            try:
                buffer = BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)

                # Agregar los datos del préstamo al PDF
                c.drawString(100, 700, f"Nombre: {nombre}")
                c.drawString(100, 680, f"Fecha de Nacimiento: {fecha_nacimiento}")
                c.drawString(100, 660, f"Dirección: {direccion}")
                c.drawString(100, 640, f"Correo: {correo}")
                c.drawString(100, 620, f"Teléfono: {telefono}")
                c.drawString(100, 600, f"Institución: {institucion}")

                # Agregar la tabla de libros al PDF
                data = [["Autor", "Titulo", "Código", "Piezas"]]
                for libro in libros:
                    data.append(
                        [
                            libro["autor"],
                            libro["titulo"],
                            libro["codigo"],
                            piezas_solicitadas_str,
                        ]
                    )

                table = Table(data)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                table.wrapOn(c, 400, 200)
                table.drawOn(c, 100, 500)

                c.showPage()
                c.save()

                buffer.seek(0)

                # Enviar el PDF como respuesta con el nombre de archivo adecuado
                response = make_response(send_file(buffer, mimetype="application/pdf"))
                response.headers[
                    "Content-Disposition"
                ] = f"attachment; filename=prestamo.pdf"
                return response

            except Exception as e:
                traceback.print_exc()  # Mostrar el error en la consola
                flash("Ocurrió un error al generar el préstamo.", "danger")
                return redirect(f"/libros/prestamo/{libro_id}")
        else:
            mensaje_error = "No se encontraron libros válidos para generar el préstamo."
            return render_template(
                "formulario_prestamo.html",
                libro_id=libro_id,
                mensaje_error=mensaje_error,
            )

    # Si es un GET, mostrar el formulario
    return render_template("formulario_prestamo.html", libro_id=libro_id)


@app.route("/autor_info", methods=["GET", "POST"])
def autor_info():
    if request.method == "POST":
        nombre_autor = request.form["nombreautor"]
        fecha_nacimiento = request.form["fecha_nacimiento"]
        nacionalidad = request.form["nacionalidad"]
        informacion = request.form["informacion"]
        imagen = request.files["imagen"] if "imagen" in request.files else None

        # Guardar la imagen en el sistema de archivos
        if imagen:
            # Obtener solo el nombre de la imagen sin la ruta completa
            imagen_nombre = imagen.filename

            # Obtener la ruta donde se guardará la imagen
            directorio_imagenes = "static/imagenes/imgau"
            if not os.path.exists(directorio_imagenes):
                os.makedirs(directorio_imagenes)

            ruta_imagen = os.path.join(directorio_imagenes, imagen_nombre)

            imagen.save(ruta_imagen)
        else:
            imagen_nombre = None

        # Guardar la información en la base de datos
        cur = mysql.connection.cursor()
        sql = "INSERT INTO autores (nombreautor, fecha_nacimiento, nacionalidad, informacion, img) VALUES (%s, %s, %s, %s, %s)"
        valores = (
            nombre_autor,
            fecha_nacimiento,
            nacionalidad,
            informacion,
            imagen_nombre,  # Usar el nombre de la imagen en lugar de la ruta completa
        )
        cur.execute(sql, valores)
        mysql.connection.commit()
        cur.close()

        flash("Información del autor guardada exitosamente!")
        return redirect("/autores")

    return render_template("autor_info.html")


@app.route("/autores")
def listar_autores():
    cur = mysql.connection.cursor()
    sql = "SELECT * FROM autores"
    cur.execute(sql)
    autores = cur.fetchall()
    cur.close()

    return render_template("autores.html", autores=autores)


@app.route("/autores")
def autores_ver():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM autores")
    autores = cur.fetchall()
    cur.close()

    return render_template("autores.html", autores=autores)


@app.route("/eliminar_autor/<int:autor_id>")
def eliminar_autor(autor_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM autores WHERE idAutores = %s", (autor_id,))
    mysql.connection.commit()
    cur.close()

    flash("Autor eliminado exitosamente!")
    return redirect("/autores")


@app.route("/buscar_autor", methods=["GET", "POST"])
def buscar_autor():
    if request.method == "POST":
        nombre_autor = request.form["nombre_autor"]
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM autores WHERE nombreautor LIKE %s",
            ("%" + nombre_autor + "%",),
        )
        autores = cur.fetchall()
        cur.close()
        return render_template("autores.html", autores=autores)

    return redirect("/autores")


@app.route("/editar_autor/<int:id>", methods=["GET", "POST"])
def editar_autor(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM autores WHERE idAutores = %s", (id,))
    autor = cur.fetchone()
    cur.close()

    if autor:
        if request.method == "POST":
            nombre_autor = request.form["nombre_autor"]
            fecha_nacimiento = request.form["fecha_nacimiento"]
            nacionalidad = request.form["nacionalidad"]
            informacion = request.form["informacion"]
            nueva_imagen = (
                request.files["imagen_nueva"]
                if "imagen_nueva" in request.files
                else None
            )

            if nueva_imagen:
                directorio_imagenes = "static/imagenes/imgau"
                if not os.path.exists(directorio_imagenes):
                    os.makedirs(directorio_imagenes)

                ruta_imagen = os.path.join(
                    directorio_imagenes, secure_filename(nueva_imagen.filename)
                )
                nueva_imagen.save(ruta_imagen)
                imagen = nueva_imagen.filename
            else:
                imagen = autor[5]  # Mantener la imagen existente

            cur = mysql.connection.cursor()
            sql = "UPDATE autores SET nombreautor=%s, fecha_nacimiento=%s, nacionalidad=%s, informacion=%s, img=%s WHERE idAutores=%s"
            valores = (
                nombre_autor,
                fecha_nacimiento,
                nacionalidad,
                informacion,
                imagen,
                id,
            )
            cur.execute(sql, valores)
            mysql.connection.commit()
            cur.close()

            flash("Información del autor actualizada exitosamente.")
            return redirect("/autores")

        return render_template("editar_autor.html", autor=autor)

    flash("Autor no encontrado o no se puede editar.")
    return redirect("/autores")


@app.route("/ver_autor/<int:id>", methods=["GET"])
def ver_autor(id):
    cur = mysql.connection.cursor()
    sql = "SELECT nombreautor, fecha_nacimiento, nacionalidad, informacion, img FROM autores WHERE idAutores = %s"
    cur.execute(sql, (id,))
    autor = cur.fetchone()
    cur.close()

    if not autor:
        flash("No se encontró el autor")
        return redirect("/autores")

    return render_template("detalle_autor.html", autor=autor)


@app.route("/inventario")
def inventario():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT idLibros, titulo, Autor, codigo_barras, categoria, piezas, fecha_publicacion FROM libros"
    )
    libros = cur.fetchall()
    cur.close()

    return render_template("inventario.html", libros=libros)


@app.route("/usuario/agregar", methods=["GET", "POST"])
def usuario_agregar():
    error_username = None
    error_email = None

    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        contraseña = request.form["contrasena"]
        hashed_contraseña = generate_password_hash(contraseña)
        fecha_nacimiento = request.form["fecha_nacimiento"]
        genero = request.form["genero"]
        curp = request.form["curp"]

        cur = mysql.connection.cursor()

        # Verificar si el nombre de usuario ya existe en la base de datos
        sql_check_username = "SELECT * FROM users WHERE username = %s"
        cur.execute(sql_check_username, (nombre,))
        existing_username = cur.fetchone()

        # Verificar si el correo electrónico ya existe en la base de datos
        sql_check_email = "SELECT * FROM users WHERE email = %s"
        cur.execute(sql_check_email, (correo,))
        existing_email = cur.fetchone()

        if existing_username:
            error_username = (
                "El nombre de usuario ya está en uso. Por favor, elija otro."
            )
        if existing_email:
            error_email = "El correo electrónico ya está en uso. Por favor, use otro."

        if not existing_username and not existing_email:
            # Generar un token de confirmación
            token = generate_confirmation_token()

            # Guardar el usuario y el token en la base de datos
            save_user_with_token(
                nombre, correo, hashed_contraseña, token, fecha_nacimiento, genero, curp
            )

            # Enviar correo de confirmación
            send_confirmation_email(correo, token)

            flash(
                "Usuario agregado exitosamente y se ha enviado un correo de confirmación."
            )

            return redirect("/usuarios")

    return render_template(
        "usuario_agregar.html", error_username=error_username, error_email=error_email
    )


# Ver usuarios
@app.route("/usuarios", methods=["GET"])
def usuarios():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users")
    usuarios = cur.fetchall()
    cur.close()

    # Supongamos que aquí se calcula la información de paginación
    paginacion_data = {
        "total_items": 100,
        "items_per_page": 10,
        "page": 1,  # Esta es la clave correcta
        "total_pages": 10,
        "has_prev": True,
        "prev_num": 1,
        "pages": [1, 2, 3, ...],  # Lista de números de páginas
        "has_next": True,
        "next_num": 2,
    }
    # Convertir los resultados de la consulta a una lista de diccionarios
    usuarios_list = []
    for usuario in usuarios:
        usuario_dict = {
            "id": usuario[0],
            "nombre": usuario[1],
            "correo": usuario[2],
        }
        usuarios_list.append(usuario_dict)

    return render_template(
        "usuarios.html", usuarios=usuarios_list, paginacion_data=paginacion_data
    )


# Editar usuario
@app.route("/usuario/editar/<int:id>", methods=["GET", "POST"])
def usuario_editar(id):
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]

        cur = mysql.connection.cursor()

        # Verificar si el nuevo nombre de usuario ya está en uso por otro usuario
        sql_check_username = "SELECT * FROM users WHERE username = %s AND id != %s"
        cur.execute(sql_check_username, (nombre, id))
        existing_username = cur.fetchone()

        # Verificar si el nuevo correo electrónico ya está en uso por otro usuario
        sql_check_email = "SELECT * FROM users WHERE email = %s AND id != %s"
        cur.execute(sql_check_email, (correo, id))
        existing_email = cur.fetchone()

        if existing_username:
            flash("El nombre de usuario ya está en uso. Por favor, elija otro.")
        elif existing_email:
            flash("El correo electrónico ya está en uso. Por favor, use otro.")
        else:
            # Actualizar el usuario en la base de datos
            sql_update_user = "UPDATE users SET username = %s, email = %s WHERE id = %s"
            valores = (nombre, correo, id)
            cur.execute(sql_update_user, valores)
            mysql.connection.commit()
            cur.close()

            flash("Usuario actualizado exitosamente!")

        return redirect("/usuarios")

    cur = mysql.connection.cursor()
    sql = "SELECT * FROM users WHERE id = %s"
    cur.execute(sql, (id,))
    usuario = cur.fetchone()
    cur.close()

    if usuario is None:
        flash("El usuario no existe")
        return redirect("/usuarios")

    return render_template("usuario_editar.html", usuario=usuario)


# Borrar usuario
@app.route("/usuario/borrar/<int:id>", methods=["GET", "POST"])
def usuario_borrar(id):
    if request.method == "POST":
        cur = mysql.connection.cursor()
        sql = "DELETE FROM users WHERE id = %s"
        cur.execute(sql, (id,))
        mysql.connection.commit()
        cur.close()

        flash("Usuario borrado exitosamente!")

    return redirect("/usuarios")


@app.route("/buscar_usuario", methods=["GET", "POST"])
def buscar_usuario():
    if request.method == "POST":
        keyword = request.form["keyword"]
        cur = mysql.connection.cursor()
        sql = "SELECT * FROM users WHERE username LIKE %s OR email LIKE %s"
        values = (f"%{keyword}%", f"%{keyword}%")
        cur.execute(sql, values)
        usuarios = cur.fetchall()

        # Convertir los resultados de las tuplas a diccionarios
        usuarios_list = []
        for usuario in usuarios:
            usuario_dict = {
                "id": usuario[0],
                "nombre": usuario[1],
                "correo": usuario[2],
                # Asegúrate de manejar la contraseña adecuadamente
            }
            usuarios_list.append(usuario_dict)

        cur.close()
        return render_template("usuarios.html", usuarios=usuarios_list)

    return redirect("/usuarios")


@app.route("/usuarios/ver/<int:id>")
def detalle_usuario(id):
    cur = mysql.connection.cursor()
    sql = "SELECT * FROM users WHERE id = %s"
    cur.execute(sql, (id,))
    usuario = cur.fetchone()
    cur.close()

    if usuario:
        return render_template("detalle_usuario.html", usuario=usuario)
    else:
        flash("Usuario no encontrado.", "danger")
        return redirect("/usuarios")


@app.route("/ver_credencial", methods=["GET"])
@login_required
def ver_credencial():
    username = current_user.username

    # Obtener los datos del usuario de la tabla users
    cur = mysql.connection.cursor()
    sql = "SELECT id, username, email, fecha_nacimiento, genero, curp FROM users WHERE username = %s"
    cur.execute(sql, (username,))
    resultado = cur.fetchone()
    cur.close()

    if resultado:
        id_usuario, username, email, fecha_nacimiento, genero, curp = resultado
        return render_template(
            "credencial.html",
            username=username,
            email=email,
            fecha_nacimiento=fecha_nacimiento,
            genero=genero,
            curp=curp,
        )
    else:
        return "No se encontraron datos de usuario"


def pagina_no_encontrada(error):
    return redirect(url_for("index"))


def acceso_no_autorizado(error):
    return redirect(url_for("login"))


if __name__ == "__main__":
    csrf.init_app(app)
    app.register_blueprint(custom_tags)
    app.register_error_handler(404, pagina_no_encontrada)
    app.register_error_handler(401, acceso_no_autorizado)
    app.run(host="0.0.0.0", port=8000)
