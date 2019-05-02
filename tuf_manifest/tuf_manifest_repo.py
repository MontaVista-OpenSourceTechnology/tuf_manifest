#!/usr/bin/env python

# Copyright 2019, MontaVista Software, LLC
# SPDX-License-Identifier: MIT

import tuf.scripts.repo

def create_argument_parser():
    parser = tuf.scripts.repo.create_argument_parser()
    return parser

def process_arguments(arguments):
    tuf.scripts.repo.process_arguments(arguments)

def parse_arguments():
    parser = create_argument_parser()

    parsed_args = parser.parse_args()

    tuf.scripts.repo.process_log_arguments(parsed_args)

    return parsed_args

