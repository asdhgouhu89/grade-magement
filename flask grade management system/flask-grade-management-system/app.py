from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# 配置数据库
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 定义数据模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='student')  # 'admin', 'teacher', 'student'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10))
    class_name = db.Column(db.String(50))
    
    # 关联成绩
    grades = db.relationship('Grade', backref='student', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credit = db.Column(db.Float)
    
    # 关联成绩
    grades = db.relationship('Grade', backref='course', lazy=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    semester = db.Column(db.String(50))

# 创建数据库表
with app.app_context():
    db.create_all()

# 路由定义
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['username'] = username
            session['role'] = user.role
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误！', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    flash('已成功退出登录！', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在！', 'error')
            return redirect(url_for('register'))
        
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功！请登录', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# 学生管理路由
@app.route('/students')
def students():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    students = Student.query.all()
    return render_template('students.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'username' not in session or session['role'] != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        name = request.form['name']
        gender = request.form['gender']
        class_name = request.form['class_name']
        
        if Student.query.filter_by(student_id=student_id).first():
            flash('学号已存在！', 'error')
            return redirect(url_for('add_student'))
        
        new_student = Student(
            student_id=student_id,
            name=name,
            gender=gender,
            class_name=class_name
        )
        
        db.session.add(new_student)
        db.session.commit()
        
        flash('学生添加成功！', 'success')
        return redirect(url_for('students'))
    
    return render_template('add_student.html')

@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    if 'username' not in session or session['role'] != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        student.student_id = request.form['student_id']
        student.name = request.form['name']
        student.gender = request.form['gender']
        student.class_name = request.form['class_name']
        
        db.session.commit()
        flash('学生信息更新成功！', 'success')
        return redirect(url_for('students'))
    
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:id>')
def delete_student(id):
    if 'username' not in session or session['role'] != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    student = Student.query.get_or_404(id)
    
    # 先删除相关的成绩记录
    Grade.query.filter_by(student_id=id).delete()
    
    db.session.delete(student)
    db.session.commit()
    
    flash('学生删除成功！', 'success')
    return redirect(url_for('students'))

# 课程管理路由
@app.route('/courses')
def courses():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    courses = Course.query.all()
    return render_template('courses.html', courses=courses)

@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if 'username' not in session or session['role'] != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        course_id = request.form['course_id']
        name = request.form['name']
        credit = request.form['credit']
        
        if Course.query.filter_by(course_id=course_id).first():
            flash('课程编号已存在！', 'error')
            return redirect(url_for('add_course'))
        
        new_course = Course(
            course_id=course_id,
            name=name,
            credit=credit
        )
        
        db.session.add(new_course)
        db.session.commit()
        
        flash('课程添加成功！', 'success')
        return redirect(url_for('courses'))
    
    return render_template('add_course.html')

@app.route('/edit_course/<int:id>', methods=['GET', 'POST'])
def edit_course(id):
    if 'username' not in session or session['role'] != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    course = Course.query.get_or_404(id)
    
    if request.method == 'POST':
        course.course_id = request.form['course_id']
        course.name = request.form['name']
        course.credit = request.form['credit']
        
        db.session.commit()
        flash('课程信息更新成功！', 'success')
        return redirect(url_for('courses'))
    
    return render_template('edit_course.html', course=course)

@app.route('/delete_course/<int:id>')
def delete_course(id):
    if 'username' not in session or session['role'] != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    course = Course.query.get_or_404(id)
    
    # 先删除相关的成绩记录
    Grade.query.filter_by(course_id=id).delete()
    
    db.session.delete(course)
    db.session.commit()
    
    flash('课程删除成功！', 'success')
    return redirect(url_for('courses'))

# 成绩管理路由
@app.route('/grades')
def grades():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if session['role'] == 'student':
        # 学生只能查看自己的成绩
        student = Student.query.filter_by(student_id=session['username']).first()
        if student:
            grades = Grade.query.filter_by(student_id=student.id).all()
            return render_template('grades.html', grades=grades)
        else:
            flash('未找到学生信息！', 'error')
            return redirect(url_for('index'))
    else:
        # 管理员和教师可以查看所有成绩
        grades = Grade.query.all()
        return render_template('grades.html', grades=grades)

@app.route('/add_grade', methods=['GET', 'POST'])
def add_grade():
    if 'username' not in session or (session['role'] != 'admin' and session['role'] != 'teacher'):
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    students = Student.query.all()
    courses = Course.query.all()
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        score = request.form['score']
        semester = request.form['semester']
        
        # 检查是否已存在该学生该课程的成绩记录
        if Grade.query.filter_by(student_id=student_id, course_id=course_id).first():
            flash('该学生该课程已有成绩记录！', 'error')
            return redirect(url_for('add_grade'))
        
        new_grade = Grade(
            student_id=student_id,
            course_id=course_id,
            score=score,
            semester=semester
        )
        
        db.session.add(new_grade)
        db.session.commit()
        
        flash('成绩添加成功！', 'success')
        return redirect(url_for('grades'))
    
    return render_template('add_grade.html', students=students, courses=courses)

@app.route('/edit_grade/<int:id>', methods=['GET', 'POST'])
def edit_grade(id):
    if 'username' not in session or (session['role'] != 'admin' and session['role'] != 'teacher'):
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    grade = Grade.query.get_or_404(id)
    students = Student.query.all()
    courses = Course.query.all()
    
    if request.method == 'POST':
        grade.student_id = request.form['student_id']
        grade.course_id = request.form['course_id']
        grade.score = request.form['score']
        grade.semester = request.form['semester']
        
        db.session.commit()
        flash('成绩更新成功！', 'success')
        return redirect(url_for('grades'))
    
    return render_template('edit_grade.html', grade=grade, students=students, courses=courses)

@app.route('/delete_grade/<int:id>')
def delete_grade(id):
    if 'username' not in session or (session['role'] != 'admin' and session['role'] != 'teacher'):
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    grade = Grade.query.get_or_404(id)
    
    db.session.delete(grade)
    db.session.commit()
    
    flash('成绩删除成功！', 'success')
    return redirect(url_for('grades'))

# 统计分析路由
@app.route('/statistics')
def statistics():
    if 'username' not in session or (session['role'] != 'admin' and session['role'] != 'teacher'):
        flash('权限不足！', 'error')
        return redirect(url_for('index'))
    
    # 计算平均分、最高分、最低分等统计数据
    courses = Course.query.all()
    course_stats = []
    
    for course in courses:
        grades = Grade.query.filter_by(course_id=course.id).all()
        if grades:
            scores = [grade.score for grade in grades]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            # 计算各分数段人数
            excellent = len([s for s in scores if s >= 90])
            good = len([s for s in scores if 80 <= s < 90])
            medium = len([s for s in scores if 70 <= s < 80])
            pass_score = len([s for s in scores if 60 <= s < 70])
            fail = len([s for s in scores if s < 60])
            
            course_stats.append({
                'course': course,
                'student_count': len(grades),
                'avg_score': round(avg_score, 2),
                'max_score': max_score,
                'min_score': min_score,
                'excellent': excellent,
                'good': good,
                'medium': medium,
                'pass': pass_score,
                'fail': fail
            })
    
    return render_template('statistics.html', course_stats=course_stats)

if __name__ == '__main__':
    app.run(debug=True)
