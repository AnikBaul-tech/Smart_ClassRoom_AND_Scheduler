import { registeredFaculty } from '../../service/Faculty/authServices.js';
import asyncHandler from '../../utils/asyncHandler.js';
import { StatusCodes } from 'http-status-codes';
import { randomUUID } from 'crypto';
import { loggedInFaculty } from '../../service/Faculty/authServices.js';

export const registerFaculty = asyncHandler(async (req, res) => {
  const facultyData = req.body;

  facultyData.id = randomUUID();

  const { faculty, token } = registeredFaculty(facultyData);

  res.cookie('token', token);

  res.status(StatusCodes.CREATED).json({
    success: true,
    faculty: {
      id: faculty.id,
      name: faculty.name,
      email: faculty.email,
    },
  });
});

export const loginFaculty = asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  const { faculty, token } = await loggedInFaculty(email, password);

  res.cookie('token', token);

  res.status(StatusCodes.CREATED).json({
    success: true,
    faculty: {
      id: faculty.id,
      name: faculty.name,
      email: faculty.email,
    },
  });
});
