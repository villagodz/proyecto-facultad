from flask import Flask, render_template, request, redirect, flash, url_for, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

#sesion_iniciar
app.secret_key = 'clave_de_sesion'

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_HOST'] = '127.0.0.1' #localHost
app.config['MYSQL_DB'] = 'proyecto-facu'

mysql= MySQL(app)


#DEFINIMOS LAS RUTAS PARA MIS PAGINAS
@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute('SELECT idCliente, cedulaCliente, nombreCliente, apellidoCliente FROM clientes')

    data = cur.fetchall()
    cur.close()
    return render_template('CLIENTES/index.html', clientes = data)

@app.route('/productos')
def productos():
    cur = mysql.connection.cursor()
    cur.execute('SELECT idProducto, nombreProducto, precioUnit FROM productos')

    data = cur.fetchall()
    cur.close()
    return render_template('PRODUCTOS/productos.html', productos = data)

@app.route('/pedidos')
def pedidos():
    cur = mysql.connection.cursor()

    # Obtener el último idPedido
    cur.execute('SELECT MAX(idPedido) FROM pedidos')
    ultimo_pedido = (cur.fetchone()[0] or 0) + 1  # Si no hay pedidos, será 0
    
    # Obtener clientes
    cur.execute('SELECT idCliente, nombreCliente, apellidoCliente FROM clientes')
    clientes = cur.fetchall()
    
    # Obtener productos
    cur.execute('SELECT idProducto, nombreProducto, precioUnit FROM productos')
    productos = cur.fetchall()
    
    # Obtener servicios para el último pedido
    cur.execute('SELECT idServicio, idItem, cantidadServicio FROM servicios WHERE idPedido = %s', (ultimo_pedido,))
    servicios = cur.fetchall()
    
    # Calcular el total del pedido
    cur.execute("""
        SELECT SUM(s.cantidadServicio * p.precioUnit) AS total
        FROM servicios s
        JOIN productos p ON s.idItem = p.idProducto
        WHERE s.idPedido = %s
    """, (ultimo_pedido,))
    total = cur.fetchone()[0] or 0
    
    cur.close()
    
    return render_template('PEDIDOS/cargaPedidos.html', clientes=clientes, productos=productos, servicios=servicios, total=total)


#DEFINIMOS LAS FUNCIONES DE RUTA

#RUTA ADD CLIENTE
@app.route('/add_cliente', methods= ['POST'])
def add_cliente():
    if request.method == 'POST':
        ci = request.form["cedulaCliente"]
        nombre = request.form["nombreCliente"]
        apellido = request.form["apellidoCliente"]

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO clientes (cedulaCliente, nombreCliente, apellidoCliente) VALUES (%s,%s,%s)", (ci, nombre, apellido))
        mysql.connection.commit()
        flash("Cliente agregado")
    return redirect(url_for('index'))

# RUTA ADD SERVICIO
@app.route("/add_servicio", methods=["POST"])
def add_servicio():
    if request.method == 'POST':
        # Obtener el último idPedido
        cur = mysql.connection.cursor()
        cur.execute('SELECT MAX(idPedido) FROM pedidos')
        ultimo_pedido = (cur.fetchone()[0] or 0) + 1  # Si no hay pedidos, será 0

        idPedido = ultimo_pedido
        idItem = request.form['idProducto']
        cantidadServicio = int(request.form['cantidad'])
        
        # Crear el servicio
        cur.execute("INSERT INTO servicios (idPedido, idItem, cantidadServicio) VALUES (%s, %s, %s)", (idPedido, idItem, cantidadServicio))
        mysql.connection.commit()
        
        # Calcular el nuevo total del pedido sumando los servicios
        cur.execute("""
            SELECT SUM(s.cantidadServicio * p.precioUnit) AS total
            FROM servicios s
            JOIN productos p ON s.idItem = p.idProducto
            WHERE s.idPedido = %s
        """, (idPedido,))
        
        total = cur.fetchone()[0] or 0  # Si no hay servicios, el total es 0

        # Actualizar el total del pedido en la tabla de pedidos
        cur.execute("UPDATE pedidos SET totalPedido = %s WHERE idPedido = %s", (total, idPedido))
        mysql.connection.commit()
        
        flash("Servicio agregado exitosamente")
        return redirect(url_for('pedidos'))



@app.route('/add_pedido', methods=['POST'])
def add_pedido():
    if request.method == 'POST':
        cur = mysql.connection.cursor()

        # Obtener el último idPedido para definir el nuevo idPedido (pivot)
        cur.execute('SELECT MAX(idPedido) FROM pedidos')
        nuevo_idPedido = (cur.fetchone()[0] or 0) + 1
        
        # Recibir datos del formulario
        idCliente = request.form["idCliente"]
        direccionPedido = request.form["direccionPedido"]
        estadoPedido = "pendiente"

        # Calcular el total de los servicios relacionados a este nuevo idPedido
        cur.execute("""
            SELECT SUM(s.cantidadServicio * p.precioUnit) AS total
            FROM servicios s
            JOIN productos p ON s.idItem = p.idProducto
            WHERE s.idPedido = %s
        """, (nuevo_idPedido,))
        
        totalPedido = cur.fetchone()[0] or 0  # Si no hay servicios, el total es 0

        # Crear el pedido en la tabla de pedidos con el total calculado
        cur.execute("INSERT INTO pedidos (idPedido, direccionPedido, totalPedido, idClientePed, estadoPedido) VALUES (%s, %s, %s, %s, %s)", 
                    (nuevo_idPedido, direccionPedido, totalPedido, idCliente, estadoPedido))
        mysql.connection.commit()
        cur.close()

        flash("Pedido agregado exitosamente con el total de los servicios")
        return redirect(url_for('pedidos'))



#RUTA ADD PRODUCTO
@app.route('/add_producto', methods= ['POST'])
def add_producto():
    if request.method == 'POST':
        nombre = request.form["nombreProducto"]
        precioUnit = request.form["precioUnit"]

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO productos (nombreProducto, precioUnit) VALUES (%s,%s)", (nombre, precioUnit))
        mysql.connection.commit()
        flash("Producto agregado")
    return redirect(url_for('productos'))



#RUTA GET PRODUCTO BY ID
@app.route('/getProducto/<id>', methods = ['POST', "GET"])
def get_producto(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT idProducto, nombreProducto, precioUnit FROM productos WHERE idProducto = {0}'.format(id))
    data = cur.fetchall()
    cur.close

    return render_template('PRODUCTOS/editProductos.html', producto = data[0])


#RUTA UPDATE PRODUCTO BY ID
@app.route("/update_producto/<id>", methods=['POST'])
def update_producto(id):
    if request.method == 'POST':
        nombre = request.form['nombreProducto']
        precio = request.form['precioUnit']
        cur = mysql.connection.cursor()
        cur.execute("""
                UPDATE productos
                SET nombreProducto = %s,
                    precioUnit = %s
                WHERE idProducto = %s
                """, (nombre, precio, id))
        flash('Producto Actualizado')
        mysql.connection.commit()
        return redirect(url_for('productos'))


#ELIMINAR PRODUCTO
@app.route('/delete/<string:id>', methods = ['POST', 'GET'])
def delete_producto(id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM productos WHERE idProducto = {0}'.format(id))
    mysql.connection.commit()
    flash('Producto borrado')
    return redirect(url_for('productos'))



#FIN DE MI SERVIDOR
if __name__ == '__main__':
    app.run(debug="true")