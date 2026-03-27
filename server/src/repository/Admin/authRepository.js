import { prisma } from '../../config/prisma.js';

export const findAdminByEmail = async (email) => {
  return await prisma.admin.findUnique({
    where: { email },
  });
};

export const createAdmin = async ({ id, name, email, password }) => {
  return await prisma.admin.create({
    data: { id, name, email, password },
  });
};
