/*
  Warnings:

  - You are about to drop the `Department` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Department_Subject` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Faculty_Subject` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Group` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Program` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Room` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Section` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Subject` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `TimeSlot` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Timetable` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Year` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropForeignKey
ALTER TABLE "Department_Subject" DROP CONSTRAINT "Department_Subject_dept_id_fkey";

-- DropForeignKey
ALTER TABLE "Department_Subject" DROP CONSTRAINT "Department_Subject_subject_id_fkey";

-- DropForeignKey
ALTER TABLE "Faculty_Subject" DROP CONSTRAINT "Faculty_Subject_faculty_id_fkey";

-- DropForeignKey
ALTER TABLE "Faculty_Subject" DROP CONSTRAINT "Faculty_Subject_subuject_id_fkey";

-- DropForeignKey
ALTER TABLE "Group" DROP CONSTRAINT "Group_section_id_fkey";

-- DropForeignKey
ALTER TABLE "Section" DROP CONSTRAINT "Section_department_id_fkey";

-- DropForeignKey
ALTER TABLE "Section" DROP CONSTRAINT "Section_year_id_fkey";

-- DropForeignKey
ALTER TABLE "Student" DROP CONSTRAINT "Student_group_id_fkey";

-- DropForeignKey
ALTER TABLE "Timetable" DROP CONSTRAINT "Timetable_room_no_fkey";

-- DropForeignKey
ALTER TABLE "Timetable" DROP CONSTRAINT "Timetable_section_id_fkey";

-- DropForeignKey
ALTER TABLE "Timetable" DROP CONSTRAINT "Timetable_subject_id_fkey";

-- DropForeignKey
ALTER TABLE "Timetable" DROP CONSTRAINT "Timetable_teacher_id_fkey";

-- DropForeignKey
ALTER TABLE "Timetable" DROP CONSTRAINT "Timetable_time_slot_fkey";

-- DropForeignKey
ALTER TABLE "Year" DROP CONSTRAINT "Year_program_id_fkey";

-- DropTable
DROP TABLE "Department";

-- DropTable
DROP TABLE "Department_Subject";

-- DropTable
DROP TABLE "Faculty_Subject";

-- DropTable
DROP TABLE "Group";

-- DropTable
DROP TABLE "Program";

-- DropTable
DROP TABLE "Room";

-- DropTable
DROP TABLE "Section";

-- DropTable
DROP TABLE "Subject";

-- DropTable
DROP TABLE "TimeSlot";

-- DropTable
DROP TABLE "Timetable";

-- DropTable
DROP TABLE "Year";
