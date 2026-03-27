import { BaseError } from './baseError.js';
import { StatusCodes } from 'http-status-codes';

export class AlreadyRegisteredError extends BaseError {
  constructor(message) {
    super('User Already Registered', message, Number(StatusCodes.BAD_REQUEST));
  }
}
