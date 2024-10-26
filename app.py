from flask import Flask, render_template, request, redirect, url_for, flash, Response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import csv
import io
import os
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import base64

app = Flask(__name__)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)  # Secure random secret key
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the Student model
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(10), nullable=False)  # Consider using db.Date for a proper date field
    phone = db.Column(db.String(15), nullable=False)
    guardian = db.Column(db.String(100), nullable=False)

    # Grading fields
    quiz_grade = db.Column(db.Float, nullable=True)
    project_grade = db.Column(db.Float, nullable=True)
    recitation_grade = db.Column(db.Float, nullable=True)
    prelim_grade = db.Column(db.Float, nullable=True)
    midterm_grade = db.Column(db.Float, nullable=True)
    final_exam_grade = db.Column(db.Float, nullable=True)
    final_grade_numeric = db.Column(db.Float, nullable=True)
    final_grade_scale = db.Column(db.String(10), nullable=True)  # String for grade scale

    def __repr__(self):
        return f'<Student {self.name}>'

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        phone = request.form['phone']
        guardian = request.form['guardian']

        new_student = Student(name=name, dob=dob, phone=phone, guardian=guardian)
        db.session.add(new_student)
        db.session.commit()

        flash("Student added successfully!")
        return redirect(url_for('home'))

    return render_template('add_student.html')

@app.route('/students')
def students():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')

    # Query the database for students (filtering by search query)
    all_students = Student.query.filter(Student.name.contains(search_query)).paginate(page=page, per_page=10)

    return render_template('students.html', students=all_students.items, search_query=search_query, pagination=all_students)

@app.route('/update_student/<int:id>', methods=['GET', 'POST'])
def update_student(id):
    student = Student.query.get(id)
    if student is None:
        flash("Student not found!")
        abort(404)

    if request.method == 'POST':
        student.name = request.form['name']
        student.dob = request.form['dob']
        student.phone = request.form['phone']
        student.guardian = request.form['guardian']

        db.session.commit()
        flash("Student updated successfully!")
        return redirect(url_for('students'))

    return render_template('update_student.html', student=student)

@app.route('/delete_student/<int:id>')
def delete_student(id):
    student = Student.query.get(id)
    if student:
        db.session.delete(student)
        db.session.commit()
        flash("Student deleted successfully!")
    else:
        flash("Student not found!")
        abort(404)

    return redirect(url_for('students'))

@app.route('/search_students', methods=['GET'])
def search_students():
    query = request.args.get('query')
    matched_students = Student.query.filter(Student.name.ilike(f'%{query}%')).all()
    return render_template('students.html', students=matched_students)

def calculate_final_grade(student):
    weighted_scores = {
        'quiz': (student.quiz_grade or 0) * 0.20,
        'project': (student.project_grade or 0) * 0.15,
        'recitation': (student.recitation_grade or 0) * 0.10,
        'prelim': (student.prelim_grade or 0) * 0.15,
        'midterm': (student.midterm_grade or 0) * 0.20,
        'final_exam': (student.final_exam_grade or 0) * 0.20,
    }

    total_weighted_score = sum(weighted_scores.values())

    # Final grade calculation
    grade_scale = {
        97: '1.0', 93: '1.25', 90: '1.5', 87: '1.75',
        83: '2.0', 80: '2.25', 75: '2.5', 73: '2.75',
        70: '3.0', 67: '3.25', 65: '3.5', 60: '4.0'
    }

    for threshold, grade in grade_scale.items():
        if total_weighted_score >= threshold:
            return total_weighted_score, grade

    return total_weighted_score, '5.0'  # Return string for failing grade

@app.route('/enter_grades/<int:id>', methods=['GET', 'POST'])
def enter_grades(id):
    student = Student.query.get_or_404(id)

    if request.method == 'POST':
        student.quiz_grade = request.form.get('quiz_grade', type=float)
        student.project_grade = request.form.get('project_grade', type=float)
        student.recitation_grade = request.form.get('recitation_grade', type=float)
        student.prelim_grade = request.form.get('prelim_grade', type=float)
        student.midterm_grade = request.form.get('midterm_grade', type=float)
        student.final_exam_grade = request.form.get('final_exam_grade', type=float)

        total_weighted_score, final_grade_scale = calculate_final_grade(student)

        student.final_grade_numeric = total_weighted_score
        student.final_grade_scale = final_grade_scale  # Store the string grade scale

        db.session.commit()
        flash("Grades updated successfully!")
        return redirect(url_for('students'))

    return render_template('enter_grades.html', student=student)

@app.route('/export_grades')
def export_grades():
    students = Student.query.all()

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Name', 'Quiz', 'Project', 'Recitation', 'Prelim', 'Midterm', 'Final Exam', 'Final Grade'])
        for student in students:
            writer.writerow([
                student.name,
                student.quiz_grade,
                student.project_grade,
                student.recitation_grade,
                student.prelim_grade,
                student.midterm_grade,
                student.final_exam_grade,
                student.final_grade_numeric
            ])
        return output.getvalue()

    return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment; filename=grades.csv"})

@app.route('/grade_distribution')
def grade_distribution():
    students = Student.query.all()
    grades = [student.final_grade_numeric for student in students]

    plt.hist(grades, bins=10, edgecolor='black')
    plt.title('Grade Distribution')
    plt.xlabel('Final Numeric Grade')
    plt.ylabel('Number of Students')

    # Save the plot to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return render_template('grade_distribution.html', plot_url=plot_url)

@app.route('/upload_grades', methods=['GET', 'POST'])
def upload_grades():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and file.filename.endswith('.csv'):
            # Ensure the uploads directory exists
            os.makedirs('uploads', exist_ok=True)

            filename = secure_filename(file.filename)
            filepath = os.path.join('uploads', filename)
            file.save(filepath)

            # Process the CSV file
            with open(filepath, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        student = Student(
                            name=row['Name'],
                            dob=row['DOB'],
                            phone=row['Phone'],
                            guardian=row['Guardian'],
                            quiz_grade=float(row['Quiz']),
                            project_grade=float(row['Project']),
                            recitation_grade=float(row['Recitation']),
                            prelim_grade=float(row['Prelim']),
                            midterm_grade=float(row['Midterm']),
                            final_exam_grade=float(row['Final Exam']),
                        )
                        db.session.add(student)
                    except Exception as e:
                        flash(f"Error processing row {row}: {e}")

                db.session.commit()
                flash("Grades uploaded successfully!")
            return redirect(url_for('students'))

    return render_template('upload_grades.html')

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/enter_grades/<int:id>', methods=['GET', 'POST'])
def enter_grades(id):
    student = Student.query.get_or_404(id)

    if request.method == 'POST':
        student.quiz_grade = request.form.get('quiz_grade', type=float)
        student.project_grade = request.form.get('project_grade', type=float)
        student.recitation_grade = request.form.get('recitation_grade', type=float)
        student.prelim_grade = request.form.get('prelim_grade', type=float)
        student.midterm_grade = request.form.get('midterm_grade', type=float)
        student.final_exam_grade = request.form.get('final_exam_grade', type=float)

        # Calculate final grade and grade scale
        total_weighted_score, final_grade_scale = calculate_final_grade(student)

        student.final_grade_numeric = total_weighted_score
        student.final_grade_scale = final_grade_scale  # Ensure this is updated correctly

        db.session.commit()
        flash("Grades updated successfully!")
        return redirect(url_for('students'))

    return render_template('enter_grades.html', student=student)
