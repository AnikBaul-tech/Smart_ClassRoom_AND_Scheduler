import { registeredAdmin } from '../../service/Admin/authServices.js';
import asyncHandler from '../../utils/asyncHandler.js';
import { StatusCodes } from 'http-status-codes';
import { randomUUID } from 'crypto';
import { loggedInAdmin } from '../../service/Admin/authServices.js';

export const registerAdmin = asyncHandler(async (req, res) => {
  const adminData = req.body;

  adminData.id = randomUUID();

  const { admin, token } = registeredAdmin(adminData);

  res.cookie('token', token);

  res.status(StatusCodes.CREATED).json({
    success: true,
    admin: {
      id: admin.id,
      name: admin.name,
      email: admin.email,
    },
  });
});

export const loginAdmin = asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  const { admin, token } = await loggedInAdmin(email, password);

  res.cookie('token', token);

  res.status(StatusCodes.CREATED).json({
    success: true,
    admin: {
      id: admin.id,
      name: admin.name,
      email: admin.email,
    },
  });
});
