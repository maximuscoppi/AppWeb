import datetime
import os
from flask import Flask, render_template, request, flash, redirect , session, jsonify, g
from werkzeug.utils import secure_filename
import sqlite3
from moviepy.editor import VideoFileClip    




app = Flask(__name__)
app.config['SECRET_KEY'] = 'joaocoppi'
app.config['DATABASE'] = 'usuarios.db'



# função para conectar ao banco de dados
def get_db():
     if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory=sqlite3.Row
     return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def create_table():
    db = get_db()
    db.execute('''
         CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL,
            tema TEXT DEFAULT '#3b5998',
            img_perfil TEXT DEFAULT '/static/imagens/user.png',
            img_capa TEXT DEFAULT '/static/imagens/fundo.jpg',
            email TEXT NOT NULL
        );

''')
    

    db.execute('''
        CREATE TABLE IF NOT EXISTS postagem ( 
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               id_usuario INTEGER NOT NULL,
               post TEXT,
               arquivo TEXT,
               data_postagem TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               FOREIGN KEY (id_usuario) REFERENCES usuario(id) ON DELETE CASCADE

               );

''')
    
    db.commit()

with app.app_context():
    create_table()



@app.route("/")
def login():
    return render_template('login.html')


@app.route('/sair')
def sair():
    session.clear()
    return redirect('/')


@app.route("/acesso", methods=['POST'] )
def acesso():
    nome = request.form.get('email')
    senha = request.form.get('senha')


    db = get_db()
    usuario = db.execute('SELECT * FROM usuario WHERE(nome = ? OR email = ?) AND senha = ?', (nome,nome,senha)).fetchone() 


    if usuario:
        session['id'] = usuario['id']
        return redirect('/home')
    else:
        flash('nome e/ou senha invalidos , tente novamente!!')

        return redirect('/')
    
@app.route("/cadastro")
def cadastro():
     return render_template('cadastro.html')

@app.route("/cadastrando" , methods=['POST'])
def cadastrando():
    nome = request.form.get('nome') 
    senha = request.form.get('senha') 
    email = request.form.get('email') 
    tema = '#3b5998'
    img_capa = '/static/imagens/fundo.jpg'
    img_perfil = '/static/imagens/user.png'

    db = get_db()
    cursor = db.execute(''' 
            INSERT INTO usuario (nome, senha, tema, img_perfil, img_capa, email) VALUES (?, ?, ?, ?, ?, ?)
''', (nome, senha, tema, img_perfil, img_capa, email))
    
    db.commit()

    flash(f'seja bem vindo, {nome}!!')
    session['id'] = cursor.lastrowid
    return redirect('/home')




@app.route('/home')
def home():
    if 'id' in session:
        id_usuario = session['id']
        db = get_db()
        usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (id_usuario,)).fetchone()
        if usuario:
            nome = usuario['nome']
            tema = usuario['tema']
            img_capa = usuario['img_capa']
            img_perfil = usuario['img_perfil']

            posts = db.execute('SELECT * FROM postagem WHERE id_usuario = ? ORDER BY data_postagem DESC', (id_usuario,)).fetchall()


            return render_template('home.html',posts=posts, nome=nome, tema=tema,img_capa=img_capa, img_perfil=img_perfil)
        else:
            flash('usuario não encontrado!!')
            return redirect('/')
        
    else:
        flash('acesso restrito!!')
        return redirect('/')



@app.route('/mudarSenha', methods=['POST'])
def mudarSenha():
    senha = request.form.get('nova_Senha')
    if 'id' in session :
        id = session['id']

        db = get_db()
        db.execute('UPDATE usuario SET senha = ? WHERE id = ?', (senha, id))

        db.commit()

    flash(f'senha trocada com sucesso, nova senha: {senha}')
    return redirect('/home')

@app.route('/mudarTema', methods=['POST'])
def mudarTema():
    if 'id' in session:
        tema = request.form.get('color')
        print(tema)
        id = session['id']
        db = get_db()
        db.execute('UPDATE usuario SET tema = ? WHERE id = ?', (tema, id))

        db.commit()

    flash(f'Tema alterado com sucesso')
    return redirect('/home')

@app.route('/nova_capa', methods=['POST'])
def nova_capa():
    if 'id' in session:
        img_capa = request.files.get('nova_capa')
        id = session['id']

        db = get_db()
        usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (id,)).fetchone()
        nome = usuario['nome']
        nome_arquivo = f"foto_capa_{nome}_{id}"
        img_capa.save(os.path.join('static/imagens/fotosCapa/', nome_arquivo))
        caminho = f'/static/imagens/fotosCapa/{nome_arquivo}'
        db.execute('UPDATE usuario SET img_capa = ? WHERE id = ?', (caminho, id))
        db.commit()
    flash(f'Capa alterado com sucesso')
    return redirect('/home')


@app.route("/apagar_conta", methods=['POST'])
def apagar_conta():
    if 'id' in session:
        id_usuario = session['id']
        
        db = get_db()
        usuario = db.execute('SELECT * FROM usuario WHERE id = ?', (id_usuario,)).fetchone()

        if usuario['img_perfil'] != '/static/imagens/user.png':
            os.remove(usuario['img_perfil'])
        if usuario['img_capa'] != '/static/imagens/fundo.jpg':
            os.remove(usuario['img_capa'])
        
        db.execute("DELETE FROM usuario WHERE id = ?", (id_usuario,))
        db.commit()

        session.pop('id', None)
        flash('Conta apagada com sucesso!!! espero te ver de novo um dia.')
    else:
        flash('é necessario fazer login para essa ação!!')

    return redirect('/')



@app.route("/enviar_foto_perfir", methods=['POST'])
def enviar_foto_perfir():
    nova_foto = request.files.get('foto')
    if not nova_foto:
        flash('Nenhuma foto foi enviada. Por favor, tente novamente!')
        return redirect('/home')
    
    id = session.get('id')
    if not id:
        flash('Você precisa estar logado para alterar a sua foto de perfil!')
        return redirect('/home')
    
    db = get_db()
    usuario = db.execute("SELECT * FROM usuario WHERE id = ?", (id,)).fetchone()
    if not usuario:
        flash('Usuario não encontrado. Por favor, faça login novamente!!')
        return redirect('/home')
    
    nome_usuario = usuario['nome']
    extensao = nova_foto.filename.split('.')[-1].lower()
    novo_nome_foto = f"Foto_perfil{nome_usuario}_{id}.{extensao}"
    caminho_foto = os.path.join('static/imagens/fotosPerfil/', novo_nome_foto)

    # verificação e exclusao da foto antiga , se não for a padrão

    if usuario['img_perfil'] != '/static/imagens/user.png':
        try:
            os.remove(usuario['img_perfil'])
        except FileNotFoundError:
            print('foto anterior nao encontrada. Continuando...')
    
    nova_foto.save(caminho_foto)

    db.execute("UPDATE usuario SET img_perfil = ? WHERE id = ?", (caminho_foto, id))
    db.commit()
    
    flash('Foto de perfil atualizada com sucesso!')
    return redirect('/home')



@app.route('/novo_post', methods=['POST'])
def novo_post():
    if 'id' in session:
        id_usuario = session['id']
        post = request.form.get('texto')


        arquivo = None

        if 'imagem' in request.files and request.files['imagem'].filename != '':
            arquivo = request.files['imagem']
            caminho_arquivo = os.path.join('static/imagens/fotosPost')
            
        elif 'video' in request.files and request.files['video'].filename != '':
            arquivo = request.files['video']
            caminho_arquivo = os.path.join('static/imagens/videosPost')
            

        else:
            caminho_arquivo = ''

        if arquivo is not None:
            extasao_arquivo = arquivo.filename.split('.')[-1].lower()
            nome_arquivo = f"post_{id_usuario}_{datetime.datetime.now()}.{extasao_arquivo}"
            nome_arquivo = secure_filename(nome_arquivo)

            caminho_arquivo = os.path.join(caminho_arquivo, nome_arquivo)
            arquivo.save(caminho_arquivo)

            if extasao_arquivo in ['.mp4', '.avi', '.mov', '.wmv', '.flv']:
                clip = VideoFileClip(caminho_arquivo)
                clip.save_frame(caminho_arquivo[0] + '.jpg', t='00:00:01.000')
            
            

        db = get_db()
        db.execute('INSERT INTO postagem (id_usuario, post, arquivo) VALUES (?, ?, ?)', (id_usuario, post, caminho_arquivo))
        db.commit()

      
    flash('Postagem realizada com sucesso!!')
    return redirect('/home')



if __name__ in '__main__':
        app.run(debug=True, port=5001)