import { prisma } from '../../config/prisma.js';

export const findFacultyByEmail = async (email) => {
  return await prisma.faculty.findUnique({
    where: { email },
  });
};

export const createFaculty = async ({
  id,
  name,
  email,
  password,
  avatar,
  phone_number,
}) => {
  return await prisma.faculty.create({
    data: { id, name, email, avatar, password, phone_number },
  });
};
