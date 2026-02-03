from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from apps.core.models import User
from apps.academic.models import (
    Student, Guardian, Subject, ClassRoom, TeacherAssignment, Segment
)
import unicodedata
import re

class Command(BaseCommand):
    help = 'Importa dados reais de Professores, Alunos e Responsáveis com CPFs fictícios corrigidos'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- Iniciando Carga de Dados Reais ---")
        
        group_teachers, _ = Group.objects.get_or_create(name='Professores')
        group_guardians, _ = Group.objects.get_or_create(name='Responsáveis')
        
        # --- DADOS DOS PROFESSORES ---
        DATA_TEACHERS = """
Geografia;Year 2 manhã e tarde - Fundamental;Mr.Francolino
História;Year 3 manhã e tarde - Fundamental;Ms.Goulart
Nave;Year 4 manhã - Fundamental;Ms.Gomes
Ciências;Year 5 manhã e tarde - Fundamental;Ms.Matias
Matemática;Year 6 manhã - Fundamental;Ms.Freire
Língua portuguesa;;Ms.Labelly
Francês;Nursery Baby - Infantil;Mr.Soares
Música;Nursery 1 - Infantil;Ms.Roberto
Arte;Nursery 2  - Infantil;Ms.Amâncio
Inglês;Recepcion - Infantil;Ms. Menezes
Educação física;Year 1 - Infantil;Ms. Aguiar
;;Ms. Souza
;;Ms. Ferreira
;;Ms. Marfil
"""

        # --- DADOS DOS ALUNOS ---
        DATA_STUDENTS = """
Alexandre Hideki Maldonado;Raul Felipe Maldonado Herbas
Alice Ribeiro de Moraes;Jair Ribeiro de Jesus Junior
Aline Rosa Rodrigues;Elaine Cristina Rodrigues Rosa
Amália Eggers Wiikmann;Erika Eggers Wiikmann
Angelina Annunciato de Carvalho;Luiz Eduardo de Carvalho
Antônio Laporte Camargo;Juliana Laporte
Arthur Batista Paz;Adriana Martins da Paz
Artur Palacios Mora;Izabella Palacio de Andrade
Ayla Franchetti Abdallah;Aiman Samih Abdallah
Beatrice  Di Renzo;Romulo Martinelli
Benjamin Giannini Vieira;Juliana Zampieri Giannini
Bento de Assis Siqueira;Carolina de Siqueira
Bianca Yuki Ivanov Fukumitsu;Nathalia Vasconcelos Ivanov Fukumitsu
Bruno Kenzo Akabane;Luciano Eiji Akabane
Carlos Eduardo Avallone Estati;Gilberto Ferreira Estati
Cassio Sponda de Almeida;Marcel Pupo de Almeida
Cecília Cecin Resek B Kiss;Lajos B Kiss Filho
Cecília Mariah Sales de Siqueira;Bruno Gantus de Siqueira
Cecília Tziporah Marques Grinberg;Gabriel Ramirez Carvalho Grinberg
Charlotte Mazoco Brasil De Siqueira;Daphne Penha Brasil de Siqueira
Clara Ayumi Nakamura Mori;Mariana Harumi Nakamura
Clarisse Ortega Herrera;Nilceia Ortega da Silva
Cora Machado Guimarães Santarelli;Eduardo Ferreira dos Santos
Cristiane Miyuki Inoue;Luciane Mayumi Kato Inoue
Davi Siqueira Macedo Campos;Manoel Macedo Campos
Davi Vericio Coradi;Geisa Lelis Coradi
Eduarda Reis Santos;Wallace Moreira dos Santos
Emanuel Gonçalves de Souza;Graziela de Souza Marcelao
Enrico Nascimento de Carlo;Cicero Nascimento Junior
Enzo Mota Camilo;Fabiana Mota de Oliveira
Esther Nogueira Fialho;Daniel Gomes Fialho
Ethan Ackel Rodrigues de Lima;Leandro Rodrigues de Lima
FIORELLA DI RIENZO;Romulo Martinelli
Felipe Shimizu Pacha Vitello;Cristina Yumi Shimizu
Fernando Yashimaro Carvalho;Davidson da Rocha de Carvalho
Gabriel Hoshino Vasconcelos;Celina Hiromi Hoshino Vasconcelos
Gabriela Alboneti Miranda;Carlos Eduardo Araujo Miranda
Gael Rondão Santiago;Gustavo Henrique de Paiva Botelho Santiago
Giovanna Masutti Peixoto;Gustavo Vieira Peixoto
Giulia Ferreira Souza;Adriana Aparecida Ferreira de Souza
Glauco Fernando Ribeiro Morales do Amaral Faria;Adriano Luis Morales do Amaral Faria
Gustavo Margenet Naito;Marcio Naito Lima
Heitor Godoi de Sá;Maira Franco Godoi
Helena Capeli Cassola;Michelle Giordan Capeli
Helena Rodrigues Vilas Boas;Rodrigo Vilas Boas Correa
Henrique de Moura Garcia Pereira;Rodrigo Garcia Pereira
Igor Oliveira Vilar;Diego Cordeiro Vilar
Isaac Nakasone Moreira Santana;Samara Nakasone Moreira da Silva Santana
Isabel Octaviano de Souza;Deivis Alves de Souza
Isabel dos Santos Borin;Diego Barrotti Borin
Isabela Margenet Naito;Marcio Naito Lima
Isabella Ramos de Oliveira;Janaina Andrade Ramos
Isabella de Castro Kochi Toledo;Bruno de Castro Toledo
Joao Vitor Ribeiro de Moraes;Jair Ribeiro de Jesus Junior
Joaquim Pais de Brito;Fernando Gabriel Pereira de Brito
Joaquim Sang Braga;Livia Vieira Sang Braga
Jordan Nogueira da Siva;Rodolfo Nogueira da Silva
José Miguel Dantas de Aquino;Juliana Favaro Rigolin de Aquino
João Arthur Bernardino;Bruna Francklin
João Pedro Alboneti Miranda;Carlos Eduardo Araujo Miranda
Julia Bechelli Pio;Jefferson Denis de Oliveira Pio
Julia Pavan Sant'Anna;Ana Glaucia Pavan Magalhaes
Kamilly Rylee Monteiro;Erika Fernanda Monteiro Ramos
Kevin Eiji Tatibana Santos;Sueny Sayuri Tatibana
Lara Novais Arrivetti;Thays Novais da Silva
Lara Oliveira Umezu;Talita Lopes de Oliveira Umezu
Lara Victal da Cruz;Gabriela Costa Victal Cruz
Laura Souza Nascimento;Paolla Maria Rodrigues de Souza
Laís Randis Medeiros de Queiroz;Marcos Eduardo Medeiros de Queiroz
Lorena Silveira Crupi;Bruno Crupi
Lorenzo Agneli Todon de Freitas Barros;Natalia Agneli Todon Silva
Lorenzo Kaue Freitas de Sousa;Anderson Barbosa de Sousa
Luara Venâncio Ribeiro;Yramax Marchao Ribeiro
Lucas Souza De Oliveira;Paulo Rogerio de Oliveira
Lucca Lipari Bechelli de Pontes;Gabriela Lipari de Paula Pontes
Luísa Gonzalez Silva;Mariana Guimaraes Gonzalez
Luísa Vilas Boas Soares;Liberio Mendes Soares Junior
Maitê Rodrigues da Silva;Willian Cleiton Silva
Manuela Amaro de Melo Gonçalves;Thiago de Melo Goncalves
Manuela Fagundes Michelotti;Juarez Michelotti
Manuela Franco de Morais Curunczi;Carolina Franco de Morais Curunczi
Manuela Monteiro Santos;Luciana Monteiro Santos
Manuela Rennó Souza Valente;Tatiana Renno da Costa Souza
Manuela Santos de Paula;Anderson Siqueira de Paula
Marcel Pupo de Almeida;Marcel Pupo de Almeida
Maria Angelica Dantas Aquino;Juliana Favaro Rigolin de Aquino
Maria Antônia Coggiani Granado;Tatiana Coggiani Leite
Maria Catarina Dantas de Aquino;Juliana Favaro Rigolin de Aquino
Maria Clara Ribeiro de Oliveira;Adenilson Donizete de Oliveira
Maria Clara Sobrinho Schiochet;Jullyanna Aparecida Goncalves Sobrinho
Maria Fernanda Couto dos Santos Viana;Sergio dos Santos
Maria Fernanda Pais de Brito;Fernando Gabriel Pereira de Brito
Maria Laura Sequine Mansur;Flavia Silveira de Moraes Sequine
Maria Luiza Ferreira Rodrigues;Francisco Rodrigues
Maria Luiza Pinho de Araujo;Priscila Barbara Pinho Araujo
Maria Luiza de Paula Silva;Glaucia de Paula Silva Ori
Matheus Jun Akabane;Luciano Eiji Akabane
Maya Muniz Ancelotti El Kadri;Natale Muniz
Maya Senedin Azevedo Marques Santos;Fabiano Azevedo Marques de Souza Santos
Maya Talarico;Thales Talarico Teixeira
Maya de Oliveira Carvalho Ribeiro;Willian Carvalho Ribeiro
Miguel Coelho Borges;Marcelo de Oliveira Borges
Miguel Ferreira Guariento;Talita dos Santos Ferreira Guariento
Miya Prados Uehara;Elaine Netto Prados
Nathan Kaneki Katasho Fernandes;Sophia Mayumi Katasho
Nicolas Gasparini;Simone Rodrigues de Souza Gasparini
Nicolas Lamarca;Celina Juliete Goncalves
Nicolas Palacios Mora;Izabella Palacio de Andrade
Olívia Hannah Marques Grinberg;Vanessa Correa Marques Grinberg
Otávio Uriel Abreu;Juliana Uriel Abreu
Pedro Miguel Martins Diefenthaler;Jose Helton Nogueira Diefenthaler Junior
Rafael Canassa;Beatriz Caveden de Oliveira
Rafael Lo Duca;Gustavo Loducca
Rebeca Xavier Lucchesi;Katty Dayanne Xavier Gomes do Carmo
Sarah Olympio Thomé;Allyne Olympio de Jesus
Sofia Meneguzzo de Oliveira;Sadi Silva de Oliveira
Sofia Sousa Roberto;Rafael Roberto
Stefano Di Rienzo Martinelli;Romulo Martinelli
Theo Borba Toledo;Marcelo Henrique Toledo Santos
Theo Marins Cintra Rezende;Ana Claudia Marins de Souza Cintra
Théo Campitelli da Conceição;Bruno Wilson da Conceicao
Valentina Maria Guizilim Martins;Flavia Eduarda da Silva Paccini Guizilim
Valentina Torres Federice;Humberto Moraes Federice
Valter Leme Mariano Neto;Valter Leme Mariano Filho
Vinicius Hiroki Inoue;Luciane Mayumi Kato Inoue
Yasmin Jungers Rodrigues Martins;Bianca Jungers Vendramini
Yasmin Kaori Nagasawa;Eric Nagasawa
Yasmin Sayuri Silva;Ana Paula Mayumi Manabe Silva
Yasmin Vitória de Almeida Siqueira;Jaqueline Morais de Almeida
Ícaro Sponda de Almeida;Marcel Pupo de Almeida
Ana Clara Waiser Pavanelli;Aline Mendes Waiser Pavanelli
Ana Clara de Oliveira Dill;Savio Dill
Ana Helena Maria Dantas de Aquino;Juliana Favaro Rigolin de Aquino
Ana Laura Passos Rosa;Larissa de Oliveira Passos Jesus
Arthur Alves Ramos;Lucas Yuri Alves Ramos
Arthur Gelk Garcia;Mauricio de Carlo Garcia
Arthur Victal da Cruz;Gabriela Costa Victal Cruz
Artur Peixoto Irei Fraga;Mauricio Tsuyoshi Irei Fraga
Ayla de Paula Sanoani;Petterson de Paula Ramos Sanoani
Beatrice Di Rienzo Martinelli;Romulo Martinelli
Bella Braga Ribeiro dos Santos;Gabriel Braga Ribeiro dos Santos
Bella de Assis Siqueira;Carolina de Siqueira
Benicio Ricci Monteiro;Gabrielly Cristina Ricci Soares Monteiro
Bryan Ackel Lima;Leandro Rodrigues de Lima
Bryan Tatibana Santos;Sueny Sayuri Talibana
Camila Peixoto Irei Fraga;Mauricio Tsuyoshi Irei Fraga
Catarina Giannini Vieira;Paulo Roberto Vieira
Catarina Hashida Keller;Giordano Keller
Cecília Randis Medeiros de Queiroz;Marcos Eduardo Medeiros de Queiroz
Cecília Tziporah Marques Grinberg;Gabriel Ramirez Carvalho Mesnek Grinberg
Clara Godoi de Sá;Maira Franco Godoi
Davi Evangelista Rossi;Andressa Danielle Ferreira Evangelista
Davi Martin Nakashima de Melo;Marcelo Augusto Ruiz da Cunha Melo
ENRICO MONTEIRO JORGE;Renato Monteiro Jorge
Emanuelly Ayumi Nisiyama;Alexandre Yoshio Nisiyama
Emanuelly Martins Morales;Nelson Vieira Morales
Endi Oliveira Stankevicius Silverio;Vania Celia Ferreira Rambousek
Enrico Souza Ribeiro;Joao Bosco Ribeiro de Oliveira
Enzo Akira da Silva Makiyama;Andreia Yuko Makiyama
Eva Marques Gambale Vieira;Giuliana Correa Marques Vieira
Gabriel Henrique Berti Assunção;Evelyn Beatriz Polidoro Berti Assuncao
Gael Luige Batista;Agnaldo Antonio Batista
Heitor Bento Borovina Martinez;Gabriele Nogueira de Freitas
Heitor Mota Camilo;Fabiana Mota de Oliveira
Helena Harue Cardoso Nakai;Natalia de Campos Cardoso Nakai
Helena Moscardini Arias;Caroline Ferreira Moscardini
Helena Nogueira da Silva;Rodolfo Nogueira da Silva
Heloísa Yumi Cardoso Nakai;Natalia de Campos Cardoso Nakai
Henrique Yukio Inoue;Luciane Mayumi Kato Inoue
Henry Estevão Torres;Caio Henrique Torres
Isabela Abreu do Nascimento;Igor Marcel Abreu Ferreira
Isis Freitas de Souza;Anderson Barbosa de Sousa
Isis Rocha Salles Yamakawa;Enio Mikio Salles Yamakawa
Ivan Renato Borges Coutinho da Silva;Renato Borges Pereira dos Santos
Joaquim Cunha Lugubone Higuchi;Marcio Issao Lugubone Franco Higuchi
José Bento Coggiani Granado;Tatiana Coggiani Leite
José Francisco Dias Quintino;Alessandra de Souza Dias
João Kalil Sequine Mansur;Flavia Silveira de Moraes Sequine
João Pedro Trigo Meireles;Carolina de C M Trigo
Julian Saito Colabelo;Carlos Alberto Colabelo Junior
LIZ BORBA TOLEDO;Marcelo Henrique Toledo Santos
Lara Novais Arrivetti;Thays Novais Arrivetti da Silva
Laura Nahum Pereira;Julia Martins Nahum Pereira
Laura Rodrigues Macari;Viviane Cristina Rodrigues Macari
Laura Silveira Crupi;Brunno Crupi
Laura Valeria Nogueira Candido;Rodolfo Nogueira Candido
Lavínia Medeiros;Paulo Medeiros
Liz De Melo Batalha;Ricardo Batalha de Faria
Liz Estevão Torres;Caio Henrique Torres
Liz Raphaela Rodrigues;Raphael Leite Rodrigues
Lorena Gabriela Mostardi Rodrigues;Jayanne de Carvalho Mostardi Rodrigues
Lorena dos Santos Silva Lima;Jonathan Frutoso de Oliveira Lima
Lorenzo Augusto Torres Rodrigues;Jayanne de Carvalho Mostardi Rodrigues
Luana Oliveira Umezu;Talita Lopes de Oliveira Umezu
Luca Blanco Leal;Francisco Blanco Fernandes Junior
Lucas Vilas Boas Soares;Liberio Mendes Soares Junior
Lucca Akio Komatsu Gomiero;Izabel Midore Komatsu Gomiero
Lucca Duarte Agg;Andreza Duarte Pereira
Luis Felipe Maria Dantas de Aquino;Juliana Favaro Rigolin de Aquino
Luísa Ferreira Guariento;Talita dos Santos Ferreira Guariento
Luísa dos Santos D'Anton Reipert;Katherine dos Santos
Mallu Pacheco do Nascimento;Alexandre Felix do Nascimento
Malu Capella Accetta Prado;Bruna Capelli Accetta
Malu Linhares Yoshimura;Gabriel Yoshimura
Malu Peixoto Puerta;Mario Puerta Junior
Manuela Franco de Morais Curunczi;Carolina Franco de Morais
Maria Celeste Dantas Aquino;Juliana Favaro Rigolin de Aquino
Maria Celeste Dantas de Aquino;Juliana Favaro Rigolin de Aquino
Maria Eduarda Sako Soares;Waldir Soares da Silva
Maria Vitória Couto dos Santos Viana;Sergio dos Santos
Mariana Hiromi Inoue;Carla Akie Nakase Inoue
Martina Indalecio Bertaiolli;Jovana Serrasqueiro Indalecio Bertaiolli
Mateo Ricci Monteiro;Gabrielly Cristina Ricci Soares Monteiro
Mateus Mendes Trindade;Elizabetth Albuquerque Mendes Trindade
Matheus Nakashima de Melo;Marcelo Augusto Ruiz da Cunha Melo
Matteo Indalecio Bertaiolli;Jovana Serrasqueiro Indalecio Bertaiolli
Maurício Sales Gantus de Siqueira;Bruno Gantus de Siqueira
Maya Linhares Yoshimura;Gabriel Yoshimura
Mia Penha Brasil de Carvalho;Emmanuel Kleber de Carvalho Souza
Miguel Bassan Yokoji;Camila Peres Bassan
Miguel Prado Blasco;Diego Carneiro Sanchez Blasco
Miguel do Nascimento Romão;Naelanna do Nascimento Barbosa
Miguel dos Reis Terciotti;Eduardo Marques dos Reis Terciotti
Murillo Rodrigues Macedo;Elen Farias Rodrigues Macedo
Murilo Ferreira Peretti;Rafael Peretti Guimaraes
Pietro de Oliveira Carvalho Ribeiro;Willian Carvalho Ribeiro
Rafael Sobrinho Schiochet;Ricardo Narciso Schiochet
Rafaela Palumbo Madureira;Rodrigo Araujo Madureira
Raphael de Lima Queiroz Amaral;Camila Gaudencia de Queiroz
Raul Torres Federice;Humberto Moraes Federice
Ravi Campitelli da Conceição;Bruno Wilson da Conceicao
Sofia Midori Inoue;Carla Akie Nakase Inoue
Stella de Paula Sanoani;Petterson de Paula Ramos Sanoani
Theo de Carvalho Monaco Romero;Kelly Natsumi de Carvalho
Théo Peixoto Puerta;Mario Puerta Junior
Théo de Castro Kochi Toledo;Karen de Castro Kochi Toledo
Vicente Yuta Ferreira Takano;Emanuele Ferreira Takano
Vinicius Sipriano do Prado;Aline da Costa Sipriano
Yohan Abdo Torres;Natalia Derencio Abdo
Zach Braga Ribeiro dos Santos;Gabriel Braga Ribeiro dos Santos
Zayan Muniz Ancelotti El Kadri;Natale Muniz
"""

        # Funções Auxiliares
        def clean_text(text):
            if not text: return ""
            return text.strip()

        def generate_username(name):
            nfkd_form = unicodedata.normalize('NFKD', name)
            only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
            clean = re.sub(r'[^a-zA-Z0-9\s]', '', only_ascii).lower().split()
            
            if len(clean) >= 2:
                base = f"{clean[0]}.{clean[-1]}"
            else:
                base = clean[0]
            
            counter = 1
            username = base
            while User.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1
            return username

        with transaction.atomic():
            self.stdout.write("Processando Professores e Turmas...")
            
            for line in DATA_TEACHERS.strip().split('\n'):
                parts = line.split(';')
                if len(parts) < 3 or "Aulas" in line: continue
                
                subject_name = clean_text(parts[0])
                classroom_raw = clean_text(parts[1])
                teacher_name = clean_text(parts[2])
                
                if not teacher_name: continue

                clean_t_name = teacher_name.replace("Mr.", "").replace("Ms.", "").replace("Mrs.", "").strip()
                teacher_username = generate_username(clean_t_name)
                
                teacher_user, created = User.objects.get_or_create(
                    username=teacher_username,
                    defaults={
                        'first_name': teacher_name,
                        'email': f"{teacher_username}@lumis.com",
                        'is_staff': True
                    }
                )
                if created:
                    teacher_user.set_password('123mudar')
                    teacher_user.groups.add(group_teachers)
                    teacher_user.save()
                    self.stdout.write(f"  [PROF] Criado: {teacher_name}")

                subject = None
                if subject_name:
                    subject, _ = Subject.objects.get_or_create(name=subject_name)

                classroom = None
                if classroom_raw:
                    segment = None
                    if "Infantil" in classroom_raw or "Nursery" in classroom_raw or "Recepcion" in classroom_raw:
                        segment, _ = Segment.objects.get_or_create(name="Educação Infantil")
                    elif "Fundamental" in classroom_raw or "Year" in classroom_raw:
                        segment, _ = Segment.objects.get_or_create(name="Ensino Fundamental")
                    
                    classroom, _ = ClassRoom.objects.get_or_create(
                        name=classroom_raw,
                        defaults={'year': 2026, 'segment': segment}
                    )

                if teacher_user and subject and classroom:
                    TeacherAssignment.objects.get_or_create(
                        teacher=teacher_user,
                        subject=subject,
                        classroom=classroom
                    )

            self.stdout.write("\nProcessando Famílias...")
            processed_students = set()
            
            global_counter = 1

            for line in DATA_STUDENTS.strip().split('\n'):
                parts = line.split(';')
                if len(parts) < 2 or "Nome do Aluno" in line: continue
                
                student_name = clean_text(parts[0]).title()
                guardian_name = clean_text(parts[1]).title()
                
                if not student_name or not guardian_name: continue
                if student_name in processed_students: continue

                # Responsável
                g_username = generate_username(guardian_name)
                guardian_user = User.objects.filter(first_name__iexact=guardian_name).first()
                
                if not guardian_user:
                    guardian_user = User.objects.create(
                        username=g_username,
                        first_name=guardian_name,
                        email=f"{g_username}@pais.com"
                    )
                    guardian_user.set_password('123mudar')
                    guardian_user.groups.add(group_guardians)
                    guardian_user.save()
                    self.stdout.write(f"  [PAI] Criado: {guardian_name}")
                
                # CORREÇÃO CRÍTICA AQUI:
                # Gerar CPF com 11 dígitos exatos
                raw_nums = f"{global_counter:011d}"  # Ex: 00000000001
                # Formatar: 000.000.000-01 (14 caracteres)
                fake_cpf_fmt = f"{raw_nums[:3]}.{raw_nums[3:6]}.{raw_nums[6:9]}-{raw_nums[9:]}"
                
                guardian_profile, created = Guardian.objects.get_or_create(
                    user=guardian_user,
                    defaults={
                        'name': guardian_name,
                        'cpf': fake_cpf_fmt,
                        'phone': '11999999999'
                    }
                )

                # Aluno
                # Usar matrícula curta para não estourar o limite
                clean_name_slug = re.sub(r'[^a-zA-Z]', '', student_name.lower())[:10]
                temp_matricula = f"T-{clean_name_slug}-{global_counter}"

                student, created = Student.objects.get_or_create(
                    name=student_name,
                    defaults={
                        'registration_number': temp_matricula
                    }
                )
                
                if created:
                    student.registration_number = f"2026{student.id:04d}"
                    student.save()
                    self.stdout.write(f"  [ALUNO] Criado: {student_name}")
                    processed_students.add(student_name)
                
                student.guardians.add(guardian_profile)
                
                global_counter += 1

        self.stdout.write(self.style.SUCCESS('\nImportação Concluída com Sucesso!'))