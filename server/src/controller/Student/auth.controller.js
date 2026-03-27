import { registeredStudent } from '../../service/Student/authServices.js';
import asyncHandler from '../../utils/asyncHandler.js';
import { StatusCodes } from 'http-status-codes';
import { randomUUID } from 'crypto';
import { loggedInStudent } from '../../service/Student/authServices.js';

export const registerStudent = asyncHandler(async (req, res) => {
  const studentData = req.body;

  studentData.id = randomUUID();
  // default group: x
  studentData.group_id = 1;

  const { student, token } = await registeredStudent(studentData);
  console.log(student);

  res.cookie('token', token);

  res.status(StatusCodes.CREATED).json({
    success: true,
    student: {
      id: student.id,
      name: student.name,
      email: student.email,
    },
  });
});

export const loginStudent = asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  const { student, token } = await loggedInStudent(email, password);

  res.cookie('token', token);

  res.status(StatusCodes.CREATED).json({
    success: true,
    student: {
      id: student.id,
      name: student.name,
      email: student.email,
    },
  });
});
