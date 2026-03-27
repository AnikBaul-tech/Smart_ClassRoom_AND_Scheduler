import { BaseError } from './baseError.js';
import { StatusCodes } from 'http-status-codes';

export class InvalidUserError extends BaseError {
  constructor(message) {
    super('Invalid User', message, Number(StatusCodes.BAD_REQUEST));
  }
}
