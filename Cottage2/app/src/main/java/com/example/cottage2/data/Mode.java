/**
 * SPDX-FileCopyrightText: 2023 Steven Hartley
 *
 * See the NOTICE file(s) distributed with this work for additional
 * information regarding copyright ownership.
 *
 * This program and the accompanying materials are made available under the
 * terms of the Apache License Version 2.0 which is available at
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * SPDX-License-Identifier: Apache-2.0
 */
package com.example.cottage2.data;

import java.util.Arrays;
import java.util.Optional;

public enum Mode {
    OFF(0, "OFF"),
    GEOTHERMAL(1, "GEOTHERMAL"),
    GEO_ELECTRIC(2, "GEO_ELECTRIC"),
    ELECTRIC_OIL(3, "ELECTRIC_OIL"),
    AUTOMATIC(4, "AUTOMATIC"),

    ELECTRIC(5, "ELECTRIC"),

    INVALID(-1, "INVALID");

    private final Integer value;
    private final String name;
    private Mode(Integer value, String name) {
        this.name = name;
        this.value = value;
    }

    public String getName() {
        return this.name;
    }
    public Integer getValue() {
        return this.value;
    }

    public static Optional<Mode> fromValue(Integer value) {
        return Arrays.stream(Mode.values())
                .filter(p -> p.getValue().equals(value))
                .findAny();
    }

    public static Optional<Mode> fromName(String name) {
        return Arrays.stream(Mode.values())
                .filter(p -> p.getName().equals(name))
                .findAny();
    }

}
