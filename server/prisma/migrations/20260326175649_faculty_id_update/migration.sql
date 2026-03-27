/*
  Warnings:

  - The primary key for the `Faculty` table will be changed. If it partially fails, the table could be left without primary key constraint.

*/
-- AlterTable
ALTER TABLE "Faculty" DROP CONSTRAINT "Faculty_pkey",
ALTER COLUMN "id" SET DATA TYPE TEXT,
ADD CONSTRAINT "Faculty_pkey" PRIMARY KEY ("id");

-- AlterTable
ALTER TABLE "Student" ALTER COLUMN "group_id" SET DATA TYPE TEXT;
