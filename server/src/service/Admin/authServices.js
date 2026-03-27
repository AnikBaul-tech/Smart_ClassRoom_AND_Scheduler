import serverConfig from '../../config/serverConfig.js';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { AlreadyRegisteredError } from '../../error/alreadyRegisteredError.js';
import {
  findAdminByEmail,
  createAdmin,
} from '../../repository/Admin/authRepository.js';
import { InvalidUserError } from '../../error/invalidUserError.js';

export const registeredAdmin = async (adminData) => {
  const { id, name, email, password } = adminData;

  const isAdminAlreadyRegistered = await findAdminByEmail(email);

  if (isAdminAlreadyRegistered) {
    throw new AlreadyRegisteredError('Admin is already registered');
  }

  const hashPassword = await bcrypt.hash(password, 10);
  const admin = await createAdmin({
    id,
    name,
    email,
    password: hashPassword,
  });

  const token = jwt.sign(
    {
      id: admin.id,
    },
    serverConfig.JWT_SECRET
  );

  return {
    admin,
    token,
  };
};

export const loggedInAdmin = async (email, password) => {
  const admin = await findAdminByEmail(email);

  if (!admin) {
    throw new InvalidUserError('Invalid email or password');
  }

  const isPasswordValid = await bcrypt.compare(password, admin.password);

  if (!isPasswordValid) {
    throw new InvalidUserError('Invalid email or passowrd');
  }

  const token = jwt.sign(
    {
      id: admin.id,
    },
    process.env.JWT_SECRET
  );

  return {
    admin,
    token,
  };
};
