import serverConfig from '../../config/serverConfig.js';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { AlreadyRegisteredError } from '../../error/alreadyRegisteredError.js';
import {
  findFacultyByEmail,
  createFaculty,
} from '../../repository/Faculty/authRepository.js';
import { InvalidUserError } from '../../error/invalidUserError.js';

export const registeredFaculty = async (facultyData) => {
  const { id, name, email, avatar, password, phone_number } = facultyData;

  const isFacultyAlreadyRegistered = await findFacultyByEmail(email);

  if (isFacultyAlreadyRegistered) {
    throw new AlreadyRegisteredError('Faculty is already registered');
  }

  const hashPassword = await bcrypt.hash(password, 10);
  const faculty = await createFaculty({
    id,
    name,
    email,
    password: hashPassword,
    avatar,
    phone_number,
  });

  const token = jwt.sign(
    {
      id: faculty.id,
    },
    serverConfig.JWT_SECRET
  );

  return {
    faculty,
    token,
  };
};

export const loggedInFaculty = async (email, password) => {
  const faculty = await findFacultyByEmail(email);

  if (!faculty) {
    throw new InvalidUserError('Invalid email or password');
  }

  const isPasswordValid = await bcrypt.compare(password, faculty.password);

  if (!isPasswordValid) {
    throw new InvalidUserError('Invalid email or passowrd');
  }

  const token = jwt.sign(
    {
      id: faculty.id,
    },
    process.env.JWT_SECRET
  );

  return {
    faculty,
    token,
  };
};
