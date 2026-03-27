import { prisma } from '../../config/prisma.js';

export const findStudentByEmail = async (email) => {
  return await prisma.student.findUnique({
    where: { email },
  });
};

export const createStudent = async ({
  id,
  name,
  email,
  password,
  avatar,
  group_id,
}) => {
  return await prisma.student.create({
    data: { id, name, email, avatar, password, group_id },
  });
};

// module.exports = {
//   findStudentByEmail,
//   createStudent,
// };
