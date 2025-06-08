from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from faker import Faker
import random
from tqdm import tqdm
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'iam_demo')

# SQLAlchemy setup
Base = declarative_base()

# Association tables for many-to-many relationships
user_groups = Table(
    'user_groups', Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('group_id', String, ForeignKey('groups.name'))
)

group_roles = Table(
    'group_roles', Base.metadata,
    Column('group_id', String, ForeignKey('groups.name')),
    Column('role_id', String, ForeignKey('roles.name'))
)

role_apps = Table(
    'role_apps', Base.metadata,
    Column('role_id', String, ForeignKey('roles.name')),
    Column('app_id', String, ForeignKey('apps.name'))
)

app_permissions = Table(
    'app_permissions', Base.metadata,
    Column('app_id', String, ForeignKey('apps.name')),
    Column('permission_id', String, ForeignKey('permissions.name'))
)

# Entity tables
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String)
    groups = relationship('Group', secondary=user_groups, back_populates='users')

class Group(Base):
    __tablename__ = 'groups'
    name = Column(String, primary_key=True)
    users = relationship('User', secondary=user_groups, back_populates='groups')
    roles = relationship('Role', secondary=group_roles, back_populates='groups')

class Role(Base):
    __tablename__ = 'roles'
    name = Column(String, primary_key=True)
    groups = relationship('Group', secondary=group_roles, back_populates='roles')
    apps = relationship('App', secondary=role_apps, back_populates='roles')

class App(Base):
    __tablename__ = 'apps'
    name = Column(String, primary_key=True)
    roles = relationship('Role', secondary=role_apps, back_populates='apps')
    permissions = relationship('Permission', secondary=app_permissions, back_populates='apps')

class Permission(Base):
    __tablename__ = 'permissions'
    name = Column(String, primary_key=True)
    apps = relationship('App', secondary=app_permissions, back_populates='permissions')

class PostgresIAMDemo:
    def __init__(self):
        self.engine = create_engine(f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}')
        self.Session = sessionmaker(bind=self.engine)
        self.faker = Faker()
        
        # Configuration
        self.NUM_USERS = 100000
        self.NUM_GROUPS = 30
        self.NUM_ROLES = 30
        self.NUM_APPS = 300
        self.NUM_PERMISSIONS = 10
        
    def create_schema(self):
        """Create database schema"""
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        
    def generate_data(self):
        """Generate synthetic IAM data"""
        session = self.Session()
        
        try:
            # Create permissions
            print("Generating permissions...")
            permissions = []
            for i in range(self.NUM_PERMISSIONS):
                perm = Permission(name=f"PERMISSION_{i}")
                permissions.append(perm)
                session.add(perm)
            
            # Create apps and assign permissions
            print("Generating apps...")
            apps = []
            for i in range(self.NUM_APPS):
                app = App(name=f"APP_{i}")
                num_perms = random.randint(1, 3)
                app.permissions = random.sample(permissions, num_perms)
                apps.append(app)
                session.add(app)
            
            # Create roles and assign apps
            print("Generating roles...")
            roles = []
            for i in range(self.NUM_ROLES):
                role = Role(name=f"ROLE_{i}")
                num_apps = random.randint(10, 20)
                role.apps = random.sample(apps, num_apps)
                roles.append(role)
                session.add(role)
            
            # Create groups and assign roles
            print("Generating groups...")
            groups = []
            for i in range(self.NUM_GROUPS):
                group = Group(name=f"GROUP_{i}")
                num_roles = random.randint(2, 4)
                group.roles = random.sample(roles, num_roles)
                groups.append(group)
                session.add(group)
            
            session.commit()
            
            # Create users and assign groups
            print("Generating users...")
            batch_size = 1000
            for i in tqdm(range(0, self.NUM_USERS, batch_size)):
                batch_users = []
                for j in range(i, min(i + batch_size, self.NUM_USERS)):
                    user = User(id=f"USER_{j}", name=self.faker.name())
                    num_groups = random.randint(1, 3)
                    user.groups = random.sample(groups, num_groups)
                    batch_users.append(user)
                    session.add(user)
                session.commit()
            
            print("Data generation complete!")
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def verify_data(self):
        """Verify that data was created correctly"""
        session = self.Session()
        try:
            counts = {
                'Users': session.query(User).count(),
                'Groups': session.query(Group).count(),
                'Roles': session.query(Role).count(),
                'Apps': session.query(App).count(),
                'Permissions': session.query(Permission).count(),
                'User-Group Relations': session.query(user_groups).count(),
                'Group-Role Relations': session.query(group_roles).count(),
                'Role-App Relations': session.query(role_apps).count(),
                'App-Permission Relations': session.query(app_permissions).count()
            }
            
            print("\nData Verification:")
            for entity, count in counts.items():
                print(f"- {entity}: {count}")
                
        finally:
            session.close()

def main():
    demo = PostgresIAMDemo()
    
    print("Creating schema...")
    demo.create_schema()
    
    print("Generating synthetic data...")
    demo.generate_data()
    
    print("Verifying data...")
    demo.verify_data()

if __name__ == "__main__":
    main() 