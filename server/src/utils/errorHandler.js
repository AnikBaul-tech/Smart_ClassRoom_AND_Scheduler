import { BaseError } from '../error/baseError.js';
import { StatusCodes } from 'http-status-codes';

export const errorHandler = (error, req, res, _next) => {
  if (error instanceof BaseError) {
    return res.status(error.statusCode).json({
      success: false,
      error: error.name,
      message: error.message,
      data: null,
    });
  } else {
    return res.status(StatusCodes.INTERNAL_SERVER_ERROR).json({
      success: false,
      error: 'Internal Server Error',
      message: 'Something went wrong on server side.',
      data: null,
    });
  }
};
