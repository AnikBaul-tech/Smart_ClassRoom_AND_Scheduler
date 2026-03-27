import express from 'express';
import { registerStudent } from '../../controller/Student/auth.controller.js';
import { registerFaculty } from '../../controller/Faculty/auth.controller.js';
import { registerAdmin } from '../../controller/Admin/auth.controller.js';
import { loginStudent } from '../../controller/Student/auth.controller.js';
import { loginFaculty } from '../../controller/Faculty/auth.controller.js';
import { loginAdmin } from '../../controller/Admin/auth.controller.js';

const authRouter = express.Router();

// Register

// api/v1/auth/student/register
authRouter.post('/student/register', registerStudent);

// api/v1/auth/faculty/register
authRouter.post('/faculty/register', registerFaculty);

// api/v1/auth/admin/register
authRouter.post('/admin/register', registerAdmin);

// Login

// api/v1/auth/student/login
authRouter.post('/student/login', loginStudent);

// api/v1/auth/faculty/login
authRouter.post('/faculty/login', loginFaculty);

// api/v1/auth/admin/login
authRouter.post('/admin/login', loginAdmin);

export default authRouter;
