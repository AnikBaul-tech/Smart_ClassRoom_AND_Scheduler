import serverConfig from '../../config/serverConfig.js';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { AlreadyRegisteredError } from '../../error/alreadyRegisteredError.js';
import { InvalidUserError } from '../../error/invalidUserError.js';
import {
  findStudentByEmail,
  createStudent,
} from '../../repository/Student/authRepository.js';

export const registeredStudent = async (studentData) => {
  const { id, name, email, avatar, password, group_id } = studentData;

  const isStudentAlreadyRegistered = await findStudentByEmail(email);

  if (isStudentAlreadyRegistered) {
    throw new AlreadyRegisteredError('Student is already registered');
  }

  const hashPassword = await bcrypt.hash(password, 10);
  console.log(hashPassword);
  const student = await createStudent({
    id,
    name,
    email,
    password: hashPassword,
    avatar,
    group_id,
  });

  const token = jwt.sign(
    {
      id: student.id,
    },
    serverConfig.JWT_SECRET
  );

  return {
    student,
    token,
  };
};

export const loggedInStudent = async (email, password) => {
  const student = await findStudentByEmail(email);

  if (!student) {
    throw new InvalidUserError('Invalid email or password');
  }

  const isPasswordValid = await bcrypt.compare(password, student.password);

  if (!isPasswordValid) {
    throw new InvalidUserError('Invalid email or passowrd');
  }

  const token = jwt.sign(
    {
      id: student.id,
    },
    process.env.JWT_SECRET
  );

  return {
    student,
    token,
  };
};
